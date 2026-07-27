from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
def root() -> dict[str, str]:
    return {"service": "auth-service", "status": "hello world!"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "canary-v2"}
