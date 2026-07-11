import hashlib
import json
import time
import urllib.error
import urllib.request
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


def upload_to_cloudinary(file: UploadFile, contents: bytes) -> str:
    if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Cloudinary is not configured")

    timestamp = str(int(time.time()))
    public_id = f"{uuid.uuid4().hex}-{file.filename or 'avatar'}"
    params = {
        "folder": settings.CLOUDINARY_FOLDER,
        "public_id": public_id,
        "timestamp": timestamp,
    }
    signature_base = "&".join(f"{key}={params[key]}" for key in sorted(params)) + settings.CLOUDINARY_API_SECRET
    signature = hashlib.sha1(signature_base.encode()).hexdigest()
    fields = {
        **params,
        "api_key": settings.CLOUDINARY_API_KEY,
        "signature": signature,
    }

    boundary = uuid.uuid4().hex
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="file"; filename="{file.filename or "avatar"}"\r\n'.encode()
    )
    body.extend(f"Content-Type: {file.content_type or 'application/octet-stream'}\r\n\r\n".encode())
    body.extend(contents)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    request = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{settings.CLOUDINARY_CLOUD_NAME}/image/upload",
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Cloudinary upload failed: {detail}") from exc
    return payload["secure_url"]
