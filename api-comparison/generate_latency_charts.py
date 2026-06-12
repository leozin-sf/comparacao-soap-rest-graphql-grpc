#!/usr/bin/env python3
"""Generate latency and response-size charts from Locust *_stats.csv reports."""

from __future__ import annotations

import argparse
import csv
import math
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path


REPORT_RE = re.compile(
    r"^(?P<api>rest|graphql|soap|grpc)_(?P<language>py|ts)_(?P<users>\d+)u_stats\.csv$"
)
API_LABELS = {
    "rest": "REST",
    "graphql": "GraphQL",
    "soap": "SOAP",
    "grpc": "gRPC",
}
LANGUAGE_LABELS = {"py": "Python", "ts": "TypeScript"}
COLORS = {"py": "#e4572e", "ts": "#2563eb"}
CRUD_OPERATIONS = ("get", "post", "update", "delete")
OPERATION_LABELS = {
    "get": "GET",
    "post": "POST / CREATE",
    "update": "UPDATE",
    "delete": "DELETE",
}
READ_OPERATION_NAMES = {
    "user",
    "users",
    "music",
    "musics",
    "playlist",
    "playlists",
}


@dataclass(frozen=True)
class Result:
    api: str
    language: str
    users: int
    average_ms: float
    p95_ms: float
    average_size_bytes: float
    operation: str | None = None

    @property
    def label(self) -> str:
        return f"{API_LABELS[self.api]} {LANGUAGE_LABELS[self.language]}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Gera graficos SVG de latencia, P95 e tamanho de resposta "
            "a partir do Locust."
        )
    )
    parser.add_argument(
        "--reports",
        type=Path,
        default=Path("reports"),
        help="Diretorio com os arquivos *_stats.csv (padrao: reports).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/charts"),
        help="Diretorio de saida dos SVGs (padrao: reports/charts).",
    )
    return parser.parse_args()


def classify_operation(api: str, request_type: str, name: str) -> str | None:
    method = request_type.strip().upper()
    if api == "rest":
        if method == "GET":
            return "get"
        if method == "POST":
            return "post"
        if method in {"PATCH", "PUT"}:
            return "update"
        if method == "DELETE":
            return "delete"

    operation_name = name.rsplit("/", 1)[-1].strip().lower()
    if operation_name.startswith(("get", "list")):
        return "get"
    if api == "graphql" and operation_name in READ_OPERATION_NAMES:
        return "get"
    if operation_name.startswith("create"):
        return "post"
    if operation_name.startswith("update"):
        return "update"
    if operation_name.startswith("delete"):
        return "delete"
    return None


def grouped_operation_result(
    api: str,
    language: str,
    users: int,
    operation: str,
    rows: list[dict[str, str]],
) -> Result | None:
    matching_rows = [
        row
        for row in rows
        if classify_operation(api, row.get("Type", ""), row.get("Name", ""))
        == operation
    ]
    request_count = sum(int(row["Request Count"]) for row in matching_rows)
    if request_count == 0:
        return None

    def weighted(column: str) -> float:
        return sum(
            float(row[column]) * int(row["Request Count"])
            for row in matching_rows
        ) / request_count

    return Result(
        api=api,
        language=language,
        users=users,
        average_ms=weighted("Average Response Time"),
        p95_ms=weighted("95%"),
        average_size_bytes=weighted("Average Content Size"),
        operation=operation,
    )


def read_results(reports_dir: Path) -> list[Result]:
    results: list[Result] = []
    for path in sorted(reports_dir.glob("*_stats.csv")):
        match = REPORT_RE.match(path.name)
        if not match:
            continue

        with path.open(newline="", encoding="utf-8-sig") as report:
            rows = list(csv.DictReader(report))
            aggregated = next(
                (row for row in rows if row.get("Name") == "Aggregated"), None
            )

        if aggregated is None:
            raise ValueError(f"Linha Aggregated nao encontrada em {path}")
        if not aggregated.get("95%"):
            raise ValueError(f"Coluna 95% nao encontrada em {path}")

        api = match.group("api")
        language = match.group("language")
        users = int(match.group("users"))
        results.append(
            Result(
                api=api,
                language=language,
                users=users,
                average_ms=float(aggregated["Average Response Time"]),
                p95_ms=float(aggregated["95%"]),
                average_size_bytes=float(aggregated["Average Content Size"]),
            )
        )
        for operation in CRUD_OPERATIONS:
            operation_result = grouped_operation_result(
                api, language, users, operation, rows
            )
            if operation_result is not None:
                results.append(operation_result)

    if not results:
        raise ValueError(f"Nenhum arquivo *_stats.csv valido encontrado em {reports_dir}")
    return results


def svg_document(width: int, height: int, content: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        "<style>"
        "text{font-family:Arial,sans-serif;fill:#17202a}"
        ".title{font-size:24px;font-weight:700}"
        ".subtitle{font-size:13px;fill:#566573}"
        ".axis{stroke:#aab7b8;stroke-width:1}"
        ".grid{stroke:#e5e7e9;stroke-width:1}"
        ".label{font-size:12px}"
        ".value{font-size:12px;font-weight:700}"
        ".legend{font-size:13px}"
        "</style>\n"
        '<rect width="100%" height="100%" fill="#ffffff"/>\n'
        f"{content}\n</svg>\n"
    )


def nice_max(value: float) -> float:
    if value <= 0:
        return 1
    magnitude = 10 ** math.floor(math.log10(value))
    normalized = value / magnitude
    step = (
        1
        if normalized <= 1
        else 2
        if normalized <= 2
        else 2.5
        if normalized <= 2.5
        else 5
        if normalized <= 5
        else 10
    )
    return step * magnitude


def compact_number(value: float) -> str:
    if value >= 100:
        return f"{value:.0f}"
    if value >= 10:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_ms(value: float) -> str:
    if value >= 1000:
        return f"{compact_number(value / 1000)} s"
    return f"{compact_number(value)} ms"


def format_bytes(value: float) -> str:
    if value >= 1000:
        return f"{compact_number(value / 1000)} kB"
    return f"{compact_number(value)} B"


def metric_value(result: Result, metric: str) -> float:
    if metric == "p95":
        return result.p95_ms
    if metric == "response_size":
        return result.average_size_bytes
    return result.average_ms


def metric_label(metric: str) -> str:
    if metric == "p95":
        return "P95"
    if metric == "response_size":
        return "Tamanho medio da resposta"
    return "Latencia media"


def format_metric(value: float, metric: str) -> str:
    if metric == "response_size":
        return format_bytes(value)
    return format_ms(value)


def chart_scope(operation: str | None) -> str:
    return (
        f"operacoes {OPERATION_LABELS[operation]}"
        if operation is not None
        else "CRUD completo"
    )


def chart_subtitle(metric: str, operation: str | None) -> str:
    if metric == "response_size":
        return "Corpo medio recebido. Escala linear iniciada em zero."
    if metric == "p95" and operation is not None:
        return (
            f"Menor e melhor. P95 medio ponderado das "
            f"{chart_scope(operation)} por quantidade de requisicoes. "
            "Escala linear iniciada em zero."
        )
    return (
        f"Menor e melhor. Escopo: {chart_scope(operation)}. "
        "Escala linear iniciada em zero."
    )


def line_chart(
    api: str,
    values: list[Result],
    metric: str,
    operation: str | None = None,
) -> str:
    width, height = 900, 520
    left, right, top, bottom = 85, 35, 90, 75
    plot_width = width - left - right
    plot_height = height - top - bottom
    users = sorted({result.users for result in values})
    max_latency = nice_max(max(metric_value(result, metric) for result in values) * 1.1)

    def x_position(user_count: int) -> float:
        if len(users) == 1:
            return left + plot_width / 2
        return left + users.index(user_count) * plot_width / (len(users) - 1)

    def y_position(latency: float) -> float:
        return top + plot_height - (latency / max_latency) * plot_height

    operation_suffix = f" {OPERATION_LABELS[operation]}" if operation else ""
    parts = [
        f'<text x="{left}" y="38" class="title">{metric_label(metric)} - '
        f"{API_LABELS[api]}{operation_suffix}: "
        "Python x TypeScript</text>",
        f'<text x="{left}" y="62" class="subtitle">'
        f"{chart_subtitle(metric, operation)}</text>",
    ]

    for tick in range(6):
        value = max_latency * tick / 5
        y = y_position(value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        parts.append(
            f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="label">'
            f"{escape(format_metric(value, metric))}</text>"
        )

    parts.extend(
        [
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_height}" class="axis"/>',
            f'<line x1="{left}" y1="{top+plot_height}" x2="{width-right}" y2="{top+plot_height}" class="axis"/>',
        ]
    )

    for user_count in users:
        x = x_position(user_count)
        parts.append(
            f'<text x="{x:.1f}" y="{height-42}" text-anchor="middle" class="label">'
            f"{user_count} usuarios</text>"
        )

    for language in ("py", "ts"):
        series = sorted(
            (result for result in values if result.language == language),
            key=lambda result: result.users,
        )
        if not series:
            continue
        points = " ".join(
            f"{x_position(result.users):.1f},{y_position(metric_value(result, metric)):.1f}"
            for result in series
        )
        parts.append(
            f'<polyline points="{points}" fill="none" stroke="{COLORS[language]}" '
            'stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        for result in series:
            x = x_position(result.users)
            value = metric_value(result, metric)
            y = y_position(value)
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{COLORS[language]}"/>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{y-11:.1f}" text-anchor="middle" class="value">'
                f"{escape(format_metric(value, metric))}</text>"
            )

    legend_x = width - 260
    for index, language in enumerate(("py", "ts")):
        x = legend_x + index * 125
        parts.append(f'<rect x="{x}" y="30" width="16" height="5" fill="{COLORS[language]}"/>')
        parts.append(
            f'<text x="{x+23}" y="38" class="legend">{LANGUAGE_LABELS[language]}</text>'
        )

    return svg_document(width, height, "\n".join(parts))


def all_apis_chart(
    users: int,
    values: list[Result],
    metric: str,
    operation: str | None = None,
) -> str:
    ordered = sorted(values, key=lambda result: metric_value(result, metric))
    width = 1000
    row_height = 44
    left, right, top, bottom = 190, 110, 105, 55
    height = top + bottom + row_height * len(ordered)
    plot_width = width - left - right
    max_value = nice_max(
        max(metric_value(result, metric) for result in ordered) * 1.1
    )

    def x_position(value: float) -> float:
        ratio = value / max_value if max_value else 0
        return left + ratio * plot_width

    parts = [
        f'<text x="{left}" y="38" class="title">{metric_label(metric)} - '
        f'{OPERATION_LABELS.get(operation, "CRUD completo")} com '
        f"{users} usuarios</text>",
        f'<text x="{left}" y="62" class="subtitle">Ranking entre todas as '
        f"APIs. {chart_subtitle(metric, operation)}</text>",
    ]

    legend_x = width - 270
    for index, language in enumerate(("py", "ts")):
        x = legend_x + index * 125
        parts.append(
            f'<rect x="{x}" y="76" width="16" height="10" rx="2" '
            f'fill="{COLORS[language]}"/>'
        )
        parts.append(
            f'<text x="{x+23}" y="86" class="legend">'
            f"{LANGUAGE_LABELS[language]}</text>"
        )

    for tick in range(6):
        value = max_value * tick / 5
        x = x_position(value)
        parts.append(f'<line x1="{x:.1f}" y1="{top-15}" x2="{x:.1f}" y2="{height-bottom}" class="grid"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{height-23}" text-anchor="middle" class="label">'
            f"{escape(format_metric(value, metric))}</text>"
        )

    for index, result in enumerate(ordered):
        y = top + index * row_height
        value = metric_value(result, metric)
        bar_end = x_position(value)
        color = COLORS[result.language]
        parts.append(
            f'<text x="{left-14}" y="{y+20}" text-anchor="end" class="label">'
            f"{escape(result.label)}</text>"
        )
        parts.append(
            f'<rect x="{left}" y="{y+5}" width="{max(3, bar_end-left):.1f}" '
            f'height="22" rx="3" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{bar_end+9:.1f}" y="{y+21}" class="value">'
            f"{escape(format_metric(value, metric))}</text>"
        )

    return svg_document(width, height, "\n".join(parts))


def main() -> None:
    args = parse_args()
    results = read_results(args.reports)
    args.output.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for metric in ("average", "p95", "response_size"):
        overall_results = [
            result for result in results if result.operation is None
        ]
        for api in API_LABELS:
            api_results = [
                result for result in overall_results if result.api == api
            ]
            if api_results:
                path = args.output / f"{metric}_same_api_{api}.svg"
                path.write_text(
                    line_chart(api, api_results, metric), encoding="utf-8"
                )
                generated.append(path)

        for users in sorted({result.users for result in overall_results}):
            load_results = [
                result for result in overall_results if result.users == users
            ]
            path = args.output / f"{metric}_all_apis_{users}u.svg"
            path.write_text(
                all_apis_chart(users, load_results, metric), encoding="utf-8"
            )
            generated.append(path)

        for operation in CRUD_OPERATIONS:
            operation_results = [
                result for result in results if result.operation == operation
            ]
            for api in API_LABELS:
                api_results = [
                    result
                    for result in operation_results
                    if result.api == api
                ]
                if api_results:
                    path = (
                        args.output
                        / f"{metric}_{operation}_same_api_{api}.svg"
                    )
                    path.write_text(
                        line_chart(
                            api,
                            api_results,
                            metric,
                            operation=operation,
                        ),
                        encoding="utf-8",
                    )
                    generated.append(path)

            for users in sorted(
                {result.users for result in operation_results}
            ):
                load_results = [
                    result
                    for result in operation_results
                    if result.users == users
                ]
                path = (
                    args.output
                    / f"{metric}_{operation}_all_apis_{users}u.svg"
                )
                path.write_text(
                    all_apis_chart(
                        users,
                        load_results,
                        metric,
                        operation=operation,
                    ),
                    encoding="utf-8",
                )
                generated.append(path)

    print(f"{len(generated)} graficos gerados em {args.output}:")
    for path in generated:
        print(f"- {path}")


if __name__ == "__main__":
    main()
