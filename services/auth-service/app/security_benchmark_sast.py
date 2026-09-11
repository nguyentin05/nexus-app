import subprocess

from fastapi import APIRouter

router = APIRouter()


@router.get("/security-benchmark-command")
def unsafe_command(command: str) -> str:
    return subprocess.check_output(command, shell=True, text=True)
