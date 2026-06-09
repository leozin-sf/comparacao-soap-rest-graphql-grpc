#!/usr/bin/env python3
"""Validate that one Locust benchmark produced complete, error-free reports."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"arquivo ausente: {path}")
    with path.open(newline="", encoding="utf-8-sig") as source:
        return list(csv.DictReader(source))


def positive_int(row: dict[str, str], column: str) -> int:
    try:
        return int(row.get(column, "0"))
    except ValueError as error:
        raise ValueError(f"valor invalido em {column}: {row.get(column)!r}") from error


def validate(prefix: Path, expected_operations: int) -> None:
    stats_path = prefix.with_name(f"{prefix.name}_stats.csv")
    failures_path = prefix.with_name(f"{prefix.name}_failures.csv")
    exceptions_path = prefix.with_name(f"{prefix.name}_exceptions.csv")
    history_path = prefix.with_name(f"{prefix.name}_stats_history.csv")
    html_path = prefix.with_suffix(".html")

    stats = read_csv(stats_path)
    operations = [row for row in stats if row.get("Name") != "Aggregated"]
    aggregated = next(
        (row for row in stats if row.get("Name") == "Aggregated"),
        None,
    )
    if aggregated is None:
        raise ValueError(f"linha Aggregated ausente: {stats_path}")
    if len(operations) != expected_operations:
        raise ValueError(
            f"{stats_path}: esperado {expected_operations} operacoes, "
            f"encontrado {len(operations)}"
        )

    empty_operations = [
        row.get("Name", "<sem nome>")
        for row in operations
        if positive_int(row, "Request Count") == 0
    ]
    if empty_operations:
        raise ValueError(
            f"{stats_path}: operacoes sem requisicoes: {', '.join(empty_operations)}"
        )
    if positive_int(aggregated, "Failure Count") != 0:
        raise ValueError(
            f"{stats_path}: {aggregated['Failure Count']} falhas agregadas"
        )

    failures = read_csv(failures_path)
    failure_count = sum(positive_int(row, "Occurrences") for row in failures)
    if failure_count:
        raise ValueError(f"{failures_path}: {failure_count} falhas")

    exceptions = read_csv(exceptions_path)
    exception_count = sum(positive_int(row, "Count") for row in exceptions)
    if exception_count:
        raise ValueError(f"{exceptions_path}: {exception_count} excecoes")

    for artifact in (history_path, html_path):
        if not artifact.is_file() or artifact.stat().st_size == 0:
            raise ValueError(f"artefato ausente ou vazio: {artifact}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("prefix", type=Path)
    parser.add_argument("--expected-operations", type=int, default=15)
    args = parser.parse_args()

    validate(args.prefix, args.expected_operations)
    print(f"OK: {args.prefix}")


if __name__ == "__main__":
    main()
