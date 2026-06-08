#!/usr/bin/env python3
"""Generate comparative latency charts from Locust *_stats.csv reports."""

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


@dataclass(frozen=True)
class Result:
    api: str
    language: str
    users: int
    average_ms: float
    p95_ms: float

    @property
    def label(self) -> str:
        return f"{API_LABELS[self.api]} {LANGUAGE_LABELS[self.language]}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera graficos SVG de latencia media e P95 a partir do Locust."
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


def read_results(reports_dir: Path) -> list[Result]:
    results: list[Result] = []
    for path in sorted(reports_dir.glob("*_stats.csv")):
        match = REPORT_RE.match(path.name)
        if not match:
            continue

        with path.open(newline="", encoding="utf-8-sig") as report:
            aggregated = next(
                (row for row in csv.DictReader(report) if row.get("Name") == "Aggregated"),
                None,
            )

        if aggregated is None:
            raise ValueError(f"Linha Aggregated nao encontrada em {path}")
        if not aggregated.get("95%"):
            raise ValueError(f"Coluna 95% nao encontrada em {path}")

        results.append(
            Result(
                api=match.group("api"),
                language=match.group("language"),
                users=int(match.group("users")),
                average_ms=float(aggregated["Average Response Time"]),
                p95_ms=float(aggregated["95%"]),
            )
        )

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
    step = 1 if normalized <= 1 else 2 if normalized <= 2 else 5 if normalized <= 5 else 10
    return step * magnitude


def format_ms(value: float) -> str:
    if value >= 1000:
        return f"{value / 1000:g} s"
    return f"{value:g} ms"


def metric_value(result: Result, metric: str) -> float:
    return result.p95_ms if metric == "p95" else result.average_ms


def metric_label(metric: str) -> str:
    return "P95" if metric == "p95" else "Latencia media"


def line_chart(api: str, values: list[Result], metric: str) -> str:
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

    parts = [
        f'<text x="{left}" y="38" class="title">{metric_label(metric)} - {API_LABELS[api]}: Python x TypeScript</text>',
        f'<text x="{left}" y="62" class="subtitle">Menor e melhor. Valores da linha Aggregated do Locust.</text>',
    ]

    for tick in range(6):
        value = max_latency * tick / 5
        y = y_position(value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" class="grid"/>')
        parts.append(
            f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="label">'
            f"{escape(format_ms(value))}</text>"
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
                f"{escape(format_ms(value))}</text>"
            )

    legend_x = width - 260
    for index, language in enumerate(("py", "ts")):
        x = legend_x + index * 125
        parts.append(f'<rect x="{x}" y="30" width="16" height="5" fill="{COLORS[language]}"/>')
        parts.append(
            f'<text x="{x+23}" y="38" class="legend">{LANGUAGE_LABELS[language]}</text>'
        )

    return svg_document(width, height, "\n".join(parts))


def all_apis_chart(users: int, values: list[Result], metric: str) -> str:
    ordered = sorted(values, key=lambda result: metric_value(result, metric))
    width = 1000
    row_height = 44
    left, right, top, bottom = 190, 110, 105, 55
    height = top + bottom + row_height * len(ordered)
    plot_width = width - left - right
    positive_values = [
        metric_value(result, metric)
        for result in ordered
        if metric_value(result, metric) > 0
    ]
    min_value = max(1.0, min(positive_values) / 1.5)
    max_value = max(positive_values) * 1.25
    min_log, max_log = math.log10(min_value), math.log10(max_value)

    def x_position(value: float) -> float:
        ratio = (math.log10(max(value, min_value)) - min_log) / (max_log - min_log)
        return left + ratio * plot_width

    parts = [
        f'<text x="{left}" y="38" class="title">{metric_label(metric)} - todas as APIs com {users} usuarios</text>',
        '<text x="{left}" y="62" class="subtitle">Ranking crescente; eixo logaritmico para preservar diferencas entre poucos ms e varios segundos.</text>'.replace(
            "{left}", str(left)
        ),
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

    first_power = math.ceil(min_log)
    last_power = math.floor(max_log)
    for power in range(first_power, last_power + 1):
        value = 10**power
        x = x_position(value)
        parts.append(f'<line x1="{x:.1f}" y1="{top-15}" x2="{x:.1f}" y2="{height-bottom}" class="grid"/>')
        parts.append(
            f'<text x="{x:.1f}" y="{height-23}" text-anchor="middle" class="label">'
            f"{escape(format_ms(value))}</text>"
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
            f"{escape(format_ms(value))}</text>"
        )

    return svg_document(width, height, "\n".join(parts))


def main() -> None:
    args = parse_args()
    results = read_results(args.reports)
    args.output.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []
    for metric in ("average", "p95"):
        for api in API_LABELS:
            api_results = [result for result in results if result.api == api]
            if api_results:
                path = args.output / f"{metric}_same_api_{api}.svg"
                path.write_text(
                    line_chart(api, api_results, metric), encoding="utf-8"
                )
                generated.append(path)

        for users in sorted({result.users for result in results}):
            load_results = [result for result in results if result.users == users]
            path = args.output / f"{metric}_all_apis_{users}u.svg"
            path.write_text(
                all_apis_chart(users, load_results, metric), encoding="utf-8"
            )
            generated.append(path)

    print(f"{len(generated)} graficos gerados em {args.output}:")
    for path in generated:
        print(f"- {path}")


if __name__ == "__main__":
    main()
