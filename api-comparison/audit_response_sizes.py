#!/usr/bin/env python3
"""Audit live API response sizes and normalized payload equality."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import grpc
import requests


sys.path.insert(0, str(Path(__file__).parent / "load-tests"))
import streaming_pb2 as pb  # noqa: E402
import streaming_pb2_grpc as pbg  # noqa: E402


LANGUAGE_PORTS = {
    "Python": {"rest": 8001, "graphql": 8002, "soap": 8000, "grpc": 50051},
    "TypeScript": {
        "rest": 8011,
        "graphql": 8012,
        "soap": 8013,
        "grpc": 50052,
    },
}
RESOURCE_CONFIG = {
    "users": {
        "graphql_fields": "id name email",
        "soap_item": "UserT",
        "grpc_method": "ListUsers",
        "grpc_items": "users",
        "fields": ("id", "name", "email"),
    },
    "musics": {
        "graphql_fields": "id title artist album durationSeconds",
        "soap_item": "MusicT",
        "grpc_method": "ListMusics",
        "grpc_items": "musics",
        "fields": (
            "id",
            "title",
            "artist",
            "album",
            "duration_seconds",
        ),
    },
    "playlists": {
        "graphql_fields": "id name userId",
        "soap_item": "PlaylistT",
        "grpc_method": "ListPlaylists",
        "grpc_items": "playlists",
        "fields": ("id", "name", "user_id"),
    },
}


@dataclass(frozen=True)
class AuditResult:
    protocol: str
    language: str
    resource: str
    item_count: int
    body_bytes: int
    content_type: str
    data_sha256: str
    same_data_as_rest_python: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Consulta as APIs reais, compara o conteudo normalizado e mede "
            "o corpo serializado."
        )
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/response_sizes.csv"),
    )
    return parser.parse_args()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def canonical_hash(items: list[dict]) -> str:
    payload = json.dumps(
        items,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def normalize_json_item(resource: str, item: dict) -> dict:
    if resource == "musics":
        item = {
            **item,
            "duration_seconds": item.get(
                "duration_seconds",
                item.get("durationSeconds"),
            ),
        }
        item.pop("durationSeconds", None)
    elif resource == "playlists":
        item = {
            **item,
            "user_id": item.get("user_id", item.get("userId")),
        }
        item.pop("userId", None)
    return item


def fetch_rest(
    resource: str,
    port: int,
    limit: int,
) -> tuple[list[dict], int, str]:
    response = requests.get(
        f"http://localhost:{port}/{resource}",
        params={"limit": limit, "offset": 0},
        timeout=30,
    )
    response.raise_for_status()
    items = [
        normalize_json_item(resource, item)
        for item in response.json()
    ]
    return items, len(response.content), response.headers.get("content-type", "")


def fetch_graphql(
    resource: str,
    port: int,
    limit: int,
) -> tuple[list[dict], int, str]:
    fields = RESOURCE_CONFIG[resource]["graphql_fields"]
    query = f"{{{resource}(limit:{limit},offset:0){{{fields}}}}}"
    response = requests.post(
        f"http://localhost:{port}/graphql",
        json={"query": query},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    items = [
        normalize_json_item(resource, item)
        for item in payload["data"][resource]
    ]
    return items, len(response.content), response.headers.get("content-type", "")


def fetch_soap(
    resource: str,
    port: int,
    limit: int,
) -> tuple[list[dict], int, str]:
    singular = resource[:-1].capitalize()
    operation = f"list{singular}s"
    body = (
        '<?xml version="1.0"?>'
        '<soapenv:Envelope '
        'xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        'xmlns:tns="streaming.soap">'
        f"<soapenv:Body><tns:{operation}>"
        f"<tns:limit>{limit}</tns:limit><tns:offset>0</tns:offset>"
        f"</tns:{operation}></soapenv:Body></soapenv:Envelope>"
    )
    response = requests.post(
        f"http://localhost:{port}/",
        data=body.encode(),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": '""',
        },
        timeout=30,
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    item_tag = RESOURCE_CONFIG[resource]["soap_item"]
    fields = RESOURCE_CONFIG[resource]["fields"]
    items = []
    for element in root.iter():
        if local_name(element.tag) != item_tag:
            continue
        raw = {
            local_name(child.tag): child.text or ""
            for child in element
        }
        item = {
            field: int(raw[field])
            if field in {"id", "duration_seconds", "user_id"}
            else raw[field]
            for field in fields
        }
        items.append(item)
    return items, len(response.content), response.headers.get("content-type", "")


def fetch_grpc(
    resource: str,
    port: int,
    limit: int,
) -> tuple[list[dict], int, str]:
    config = RESOURCE_CONFIG[resource]
    with grpc.insecure_channel(f"localhost:{port}") as channel:
        stub = pbg.StreamingServiceStub(channel)
        reply = getattr(stub, config["grpc_method"])(
            pb.Page(limit=limit, offset=0),
            timeout=30,
        )
    fields = config["fields"]
    items = [
        {field: getattr(item, field) for field in fields}
        for item in getattr(reply, config["grpc_items"])
    ]
    return items, reply.ByteSize(), "application/grpc+proto"


def audit(limit: int) -> list[AuditResult]:
    fetchers = {
        "REST": fetch_rest,
        "GraphQL": fetch_graphql,
        "SOAP": fetch_soap,
        "gRPC": fetch_grpc,
    }
    captured: dict[tuple[str, str, str], tuple[list[dict], int, str]] = {}
    for resource in RESOURCE_CONFIG:
        for language, ports in LANGUAGE_PORTS.items():
            for protocol, fetcher in fetchers.items():
                captured[(protocol, language, resource)] = fetcher(
                    resource,
                    ports[protocol.lower()],
                    limit,
                )

    results = []
    for resource in RESOURCE_CONFIG:
        baseline = captured[("REST", "Python", resource)][0]
        for language in LANGUAGE_PORTS:
            for protocol in fetchers:
                items, body_bytes, content_type = captured[
                    (protocol, language, resource)
                ]
                results.append(
                    AuditResult(
                        protocol=protocol,
                        language=language,
                        resource=resource,
                        item_count=len(items),
                        body_bytes=body_bytes,
                        content_type=content_type,
                        data_sha256=canonical_hash(items),
                        same_data_as_rest_python=items == baseline,
                    )
                )
    return results


def write_csv(path: Path, results: list[AuditResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=AuditResult.__dataclass_fields__.keys(),
        )
        writer.writeheader()
        for result in results:
            writer.writerow(result.__dict__)


def main() -> None:
    args = parse_args()
    if args.limit <= 0:
        raise SystemExit("--limit deve ser maior que zero")
    results = audit(args.limit)
    write_csv(args.output, results)

    print(
        f"{'Recurso':10} {'API':8} {'Linguagem':10} "
        f"{'Itens':>5} {'Bytes':>7} {'Iguais':>7}"
    )
    for result in results:
        print(
            f"{result.resource:10} {result.protocol:8} "
            f"{result.language:10} {result.item_count:5} "
            f"{result.body_bytes:7} "
            f"{str(result.same_data_as_rest_python):>7}"
        )
    mismatches = [
        result for result in results
        if not result.same_data_as_rest_python
    ]
    if mismatches:
        raise SystemExit(
            f"{len(mismatches)} respostas divergiram do REST Python"
        )
    print(f"OK: auditoria gravada em {args.output}")
    print(
        "Nota: em gRPC, bytes correspondem ao ByteSize da mensagem "
        "Protobuf, sem headers e framing HTTP/2."
    )


if __name__ == "__main__":
    main()
