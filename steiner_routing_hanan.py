#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import resource
import sys
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[int, int]
Segment = Tuple[Point, Point]
Route = Tuple[str, List[Point], List[Segment]]


def manhattan(a: Point, b: Point) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def compute_mst(points: Sequence[Point]) -> Tuple[int, List[Tuple[Point, Point]]]:
    if not points:
        return 0, []
    n = len(points)
    in_tree = [False] * n
    min_dist = [float("inf")] * n
    parent = [-1] * n
    min_dist[0] = 0
    total = 0
    edges: List[Tuple[Point, Point]] = []

    for _ in range(n):
        u = -1
        best = float("inf")
        for i in range(n):
            if not in_tree[i] and min_dist[i] < best:
                best = min_dist[i]
                u = i
        if u == -1:
            break
        in_tree[u] = True
        total += min_dist[u]
        if parent[u] != -1:
            edges.append((points[parent[u]], points[u]))
        for v in range(n):
            if in_tree[v]:
                continue
            dist = manhattan(points[u], points[v])
            if dist < min_dist[v]:
                min_dist[v] = dist
                parent[v] = u

    return total, edges


def compute_mst_length(points: Sequence[Point]) -> int:
    if not points:
        return 0
    n = len(points)
    in_tree = [False] * n
    min_dist = [float("inf")] * n
    min_dist[0] = 0
    total = 0

    for _ in range(n):
        u = -1
        best = float("inf")
        for i in range(n):
            if not in_tree[i] and min_dist[i] < best:
                best = min_dist[i]
                u = i
        if u == -1:
            break
        in_tree[u] = True
        total += min_dist[u]
        for v in range(n):
            if in_tree[v]:
                continue
            dist = manhattan(points[u], points[v])
            if dist < min_dist[v]:
                min_dist[v] = dist

    return total


def hanan_grid(terminals: Sequence[Point]) -> List[Point]:
    xs = sorted({x for x, _ in terminals})
    ys = sorted({y for _, y in terminals})
    return [(x, y) for x in xs for y in ys]


def kahng_robins(terminals: Sequence[Point]) -> Tuple[int, List[Tuple[Point, Point]]]:
    """Compute routing with iterative 1-Steiner insertion on the Hanan grid."""
    unique_terminals = list(dict.fromkeys(terminals))
    points: List[Point] = list(unique_terminals)
    point_set = set(points)
    candidates = [
        candidate
        for candidate in hanan_grid(unique_terminals)
        if candidate not in point_set
    ]

    current_length, _ = compute_mst(points)
    while True:
        best_length = current_length
        best_index: int | None = None
        for index, candidate in enumerate(candidates):
            points.append(candidate)
            length = compute_mst_length(points)
            points.pop()
            if length < best_length:
                best_length = length
                best_index = index
        if best_index is None:
            break
        best_candidate = candidates.pop(best_index)
        points.append(best_candidate)
        point_set.add(best_candidate)
        current_length = best_length

    final_length, final_edges = compute_mst(points)
    return final_length, final_edges


def rectilinearize(edges: Iterable[Tuple[Point, Point]]) -> List[Segment]:
    segments: List[Segment] = []
    for start, end in edges:
        if start[0] == end[0] or start[1] == end[1]:
            segments.append((start, end))
            continue
        mid = (start[0], end[1])
        segments.append((start, mid))
        segments.append((mid, end))
    return segments


def parse_nets(path: Path) -> Tuple[int, int, List[Tuple[str, List[Point]]]]:
    grid_size = None
    net_count = None
    nets: List[Tuple[str, List[Point]]] = []

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+\.\s*", "", line)
        if grid_size is None:
            parts = line.split()
            if len(parts) < 2:
                raise ValueError(f"Invalid header line: {raw_line}")
            grid_size = int(parts[0])
            net_count = int(parts[1])
            continue
        match = re.match(r"^(\S+)\s*\[", line)
        if not match:
            raise ValueError(f"Invalid net line: {raw_line}")
        name = match.group(1)
        points = [
            (int(x), int(y))
            for x, y in re.findall(r"\((-?\d+)\s*,\s*(-?\d+)\)", line)
        ]
        if not points:
            raise ValueError(f"No points found for net {name}")
        nets.append((name, points))

    if grid_size is None or net_count is None:
        raise ValueError("Missing header line with grid size and net count")
    return grid_size, net_count, nets


def format_segments(segments: Sequence[Segment]) -> str:
    return " ".join(
        f"({x1},{y1}),({x2},{y2})" for (x1, y1), (x2, y2) in segments
    )


def write_output(
    path: Path, grid_size: int, net_count: int, routed: List[Tuple[str, List[Segment]]]
) -> None:
    lines = [f"{grid_size} {net_count}"]
    for name, segments in routed:
        lines.append(f"{name} [ {format_segments(segments)} ]")
    path.write_text("\n".join(lines) + "\n")


def write_svg(path: Path, grid_size: int, routes: Sequence[Route]) -> None:
    cell = 20
    margin = 20
    width = (grid_size - 1) * cell + margin * 2
    height = (grid_size - 1) * cell + margin * 2
    palette = [
        "#e41a1c",
        "#377eb8",
        "#4daf4a",
        "#984ea3",
        "#ff7f00",
        "#a65628",
        "#f781bf",
        "#999999",
    ]

    def to_svg(point: Point) -> Tuple[int, int]:
        # Input coordinates are 1-based; SVG y-axis is inverted.
        x = margin + (point[0] - 1) * cell
        y = margin + (grid_size - point[1]) * cell
        return x, y

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white" stroke="black" />',
    ]

    for i in range(grid_size):
        pos = margin + i * cell
        lines.append(
            f'<line x1="{pos}" y1="{margin}" x2="{pos}" y2="{height - margin}" '
            'stroke="#e0e0e0" stroke-width="1" />'
        )
        lines.append(
            f'<line x1="{margin}" y1="{pos}" x2="{width - margin}" y2="{pos}" '
            'stroke="#e0e0e0" stroke-width="1" />'
        )

    for index, (name, terminals, segments) in enumerate(routes):
        color = palette[index % len(palette)]
        for start, end in segments:
            x1, y1 = to_svg(start)
            x2, y2 = to_svg(end)
            lines.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
                f'stroke="{color}" stroke-width="2" />'
            )
        for point in terminals:
            x, y = to_svg(point)
            lines.append(
                f'<circle cx="{x}" cy="{y}" r="4" fill="{color}" stroke="black" />'
            )
        lines.append(
            f'<text x="{margin}" y="{15 + index * 14}" font-size="12" '
            f'fill="{color}">{name}</text>'
        )

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Steiner routing with Kahng/Robins 1-Steiner insertion using Hanan Grid optimization."
    )
    parser.add_argument("input", help="Path to .nets input file")
    args = parser.parse_args()

    start_time = time.perf_counter()

    input_path = Path(args.input).resolve()
    grid_size, net_count, nets = parse_nets(input_path)

    routed_segments: List[Tuple[str, List[Segment]]] = []
    routed_routes: List[Route] = []
    total_length = 0

    for name, terminals in nets:
        wirelength, edges = kahng_robins(terminals)
        total_length += wirelength
        segments = rectilinearize(edges)
        routed_segments.append((name, segments))
        routed_routes.append((name, terminals, segments))
        print(f"Net {name}: {wirelength}")

    print(f"Total wirelength: {total_length}")

    output_path = input_path.with_suffix(".routing")
    write_output(output_path, grid_size, net_count, routed_segments)
    print(f"Output written to: {output_path}")

    image_dir = input_path.with_suffix("")
    image_dir.mkdir(parents=True, exist_ok=True)

    image_path = image_dir / f"{input_path.stem}.routing.svg"
    write_svg(image_path, grid_size, routed_routes)
    for name, terminals, segments in routed_routes:
        net_path = image_dir / f"{name}.svg"
        write_svg(net_path, grid_size, [(name, terminals, segments)])
    print(f"Images written to: {image_dir}")

    elapsed = time.perf_counter() - start_time
    ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    max_rss_kb = ru_maxrss / 1024 if sys.platform == "darwin" else ru_maxrss
    print(f"Runtime: {elapsed:.6f}s")
    print(f"Memory usage: {max_rss_kb:.0f} KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
