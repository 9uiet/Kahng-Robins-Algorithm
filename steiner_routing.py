#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import resource
import time
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

Point = Tuple[int, int]
Segment = Tuple[Point, Point]


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
    unique_terminals = list(dict.fromkeys(terminals))
    points: List[Point] = list(unique_terminals)
    point_set = set(points)
    candidates = hanan_grid(unique_terminals)

    current_length, _ = compute_mst(points)
    while True:
        best_length = current_length
        best_candidate: Point | None = None
        for candidate in candidates:
            if candidate in point_set:
                continue
            length = compute_mst_length(points + [candidate])
            if length < best_length:
                best_length = length
                best_candidate = candidate
        if best_candidate is None:
            break
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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Steiner routing with Kahng/Robins 1-Steiner insertion."
    )
    parser.add_argument("input", help="Path to .nets input file")
    args = parser.parse_args()

    start_time = time.perf_counter()

    input_path = Path(args.input).resolve()
    grid_size, net_count, nets = parse_nets(input_path)

    routed_segments: List[Tuple[str, List[Segment]]] = []
    total_length = 0

    for name, terminals in nets:
        wirelength, edges = kahng_robins(terminals)
        total_length += wirelength
        segments = rectilinearize(edges)
        routed_segments.append((name, segments))
        print(f"Net {name}: {wirelength}")

    print(f"Total wirelength: {total_length}")

    output_path = input_path.with_suffix(".routing")
    write_output(output_path, grid_size, net_count, routed_segments)
    print(f"Output written to: {output_path}")

    elapsed = time.perf_counter() - start_time
    max_rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print(f"Runtime: {elapsed:.6f}s")
    print(f"Memory usage: {max_rss_kb} KB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
