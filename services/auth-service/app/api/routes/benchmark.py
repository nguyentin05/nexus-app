import asyncio
import logging
import socket
import ssl
import time

from fastapi import APIRouter, HTTPException, Query

from app.metrics import set_benchmark_fault

LOGGER = logging.getLogger("auth-service.benchmark")
router = APIRouter(prefix="/_benchmark", tags=["benchmark"], include_in_schema=False)


@router.post("/arm")
def arm(scenario: str, run_id: str, symptom: str) -> dict[str, str]:
    set_benchmark_fault(scenario, run_id, symptom, 1)
    return {"status": "armed", "run_id": run_id}


@router.post("/clear")
def clear(scenario: str, run_id: str, symptom: str = "cleared") -> dict[str, str]:
    set_benchmark_fault(scenario, run_id, symptom, 0)
    return {"status": "cleared", "run_id": run_id}


@router.get("/error")
def error(run_id: str) -> None:
    LOGGER.error("benchmark HTTP handler failure run_id=%s status=500", run_id)
    raise HTTPException(status_code=500, detail="controlled benchmark failure")


@router.get("/slow")
async def slow(run_id: str, seconds: float = Query(2, ge=0.1, le=10)) -> dict[str, str]:
    LOGGER.warning("benchmark slow request run_id=%s delay_seconds=%s", run_id, seconds)
    await asyncio.sleep(seconds)
    return {"status": "completed"}


@router.get("/cpu")
def cpu(run_id: str, seconds: float = Query(20, ge=1, le=60)) -> dict[str, str]:
    LOGGER.warning(
        "benchmark CPU saturation run_id=%s duration_seconds=%s", run_id, seconds
    )
    deadline = time.monotonic() + seconds
    value = 1
    while time.monotonic() < deadline:
        value = (value * 48271) % 2147483647
    return {"status": "completed", "value": str(value)}


@router.get("/memory")
def memory(run_id: str, megabytes: int = Query(512, ge=16, le=1024)) -> None:
    LOGGER.error("benchmark memory growth run_id=%s requested_mb=%s", run_id, megabytes)
    blocks = []
    while len(blocks) < megabytes:
        blocks.append(bytearray(1024 * 1024))
        time.sleep(0.01)
    raise HTTPException(status_code=500, detail="memory limit was not reached")


@router.get("/database-refused")
def database_refused(run_id: str) -> None:
    try:
        with socket.create_connection(("127.0.0.1", 9), timeout=1):
            pass
    except OSError as error:
        LOGGER.error(
            "database connection refused run_id=%s host=127.0.0.1 port=9 error=%s",
            run_id,
            error,
        )
        raise HTTPException(status_code=503, detail="database unavailable") from error
    raise HTTPException(status_code=500, detail="unexpected benchmark result")


@router.get("/dns")
def dns(run_id: str) -> None:
    try:
        socket.getaddrinfo("missing-dependency.invalid", 443)
    except socket.gaierror as error:
        LOGGER.error(
            "DNS resolution failure run_id=%s host=missing-dependency.invalid error=%s",
            run_id,
            error,
        )
        raise HTTPException(status_code=503, detail="dependency unavailable") from error
    raise HTTPException(status_code=500, detail="unexpected benchmark result")


@router.get("/dependency-timeout")
async def dependency_timeout(run_id: str) -> None:
    try:
        await asyncio.wait_for(asyncio.sleep(5), timeout=0.5)
    except TimeoutError as error:
        LOGGER.error(
            "dependency timeout run_id=%s dependency=payments timeout_seconds=0.5",
            run_id,
        )
        raise HTTPException(status_code=504, detail="dependency timeout") from error


@router.get("/certificate")
def certificate(run_id: str) -> None:
    error = ssl.SSLCertVerificationError("certificate has expired")
    LOGGER.error("TLS verification failed run_id=%s error=%s", run_id, error)
    raise HTTPException(
        status_code=502, detail="TLS certificate verification failed"
    ) from error


@router.get("/network")
def network(run_id: str) -> None:
    try:
        with socket.create_connection(
            ("aiops-benchmark-dependency.apps.svc.cluster.local", 8000),
            timeout=2,
        ):
            return
    except OSError as error:
        LOGGER.error(
            "dependency network timeout run_id=%s host=aiops-benchmark-dependency.apps.svc.cluster.local port=8000 error=%s",
            run_id,
            error,
        )
        raise HTTPException(
            status_code=504, detail="dependency network failure"
        ) from error
