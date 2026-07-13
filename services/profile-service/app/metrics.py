from collections import Counter
from time import monotonic
from typing import Callable

from fastapi import Request, Response

BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
REQUESTS: Counter[tuple[str, str, int]] = Counter()
DURATION_BUCKETS: Counter[tuple[str, str, float | str]] = Counter()
DURATION_SUMS: Counter[tuple[str, str]] = Counter()


def route_path(request: Request) -> str:
    route = request.scope.get("route")
    if not route:
        return "unmatched"
    return getattr(route, "path", "unmatched")


async def metrics_middleware(request: Request, call_next: Callable) -> Response:
    if request.url.path == "/metrics":
        return await call_next(request)

    started = monotonic()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = monotonic() - started
        method = request.method
        path = route_path(request)
        REQUESTS[(method, path, status_code)] += 1
        DURATION_SUMS[(method, path)] += elapsed
        for bucket in BUCKETS:
            if elapsed <= bucket:
                DURATION_BUCKETS[(method, path, bucket)] += 1
        DURATION_BUCKETS[(method, path, "+Inf")] += 1


def label_value(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def labels(**values: object) -> str:
    return ",".join(f'{key}="{label_value(value)}"' for key, value in values.items())


def render_metrics(service: str, version: str) -> str:
    lines = [
        "# HELP nexus_app_info Application build information.",
        "# TYPE nexus_app_info gauge",
        f'nexus_app_info{{{labels(service=service, version=version)}}} 1',
        "# HELP nexus_http_requests_total Total HTTP requests.",
        "# TYPE nexus_http_requests_total counter",
    ]

    for (method, path, status), count in sorted(REQUESTS.items()):
        lines.append(
            f'nexus_http_requests_total{{{labels(method=method, path=path, status=status)}}} {count}'
        )

    lines.extend([
        "# HELP nexus_http_request_duration_seconds HTTP request duration in seconds.",
        "# TYPE nexus_http_request_duration_seconds histogram",
    ])
    for (method, path, le), count in sorted(DURATION_BUCKETS.items(), key=lambda item: (item[0][0], item[0][1], str(item[0][2]))):
        lines.append(
            f'nexus_http_request_duration_seconds_bucket{{{labels(method=method, path=path, le=le)}}} {count}'
        )
    for (method, path), total in sorted(DURATION_SUMS.items()):
        count = DURATION_BUCKETS[(method, path, "+Inf")]
        lines.append(f'nexus_http_request_duration_seconds_count{{{labels(method=method, path=path)}}} {count}')
        lines.append(f'nexus_http_request_duration_seconds_sum{{{labels(method=method, path=path)}}} {total:.6f}')

    return "\n".join(lines) + "\n"
