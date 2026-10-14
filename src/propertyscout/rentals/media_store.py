
"""Safe local media storage for PropertyScout rental listings."""

import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MEDIA_ROOT = PROJECT_ROOT / "data" / "media" / "rentals"

MAX_IMAGE_BYTES = 10 * 1024 * 1024       # 10 MB
MAX_VIDEO_BYTES = 100 * 1024 * 1024     # 100 MB
CHUNK_SIZE = 1024 * 1024                # Read 1 MB at a time

IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

VIDEO_TYPES = {
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


def listing_media_dir(listing_id: str) -> Path:
    """Return the media directory for a valid listing ID."""
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", listing_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid listing ID.",
        )

    return MEDIA_ROOT / listing_id


async def save_upload(
    listing_id: str,
    upload: UploadFile,
) -> dict[str, str | int]:
    """Validate and save an uploaded image or video."""
    content_type = (
        (upload.content_type or "")
        .lower()
        .split(";")[0]
        .strip()
    )

    if content_type in IMAGE_TYPES:
        allowed_types = IMAGE_TYPES
        max_bytes = MAX_IMAGE_BYTES
        media_type = "image"

    elif content_type in VIDEO_TYPES:
        allowed_types = VIDEO_TYPES
        max_bytes = MAX_VIDEO_BYTES
        media_type = "video"

    else:
        await upload.close()
        raise HTTPException(
            status_code=415,
            detail=(
                "Unsupported file type. "
                "Use JPEG, PNG, WebP, MP4, or WebM."
            ),
        )

    directory = listing_media_dir(listing_id)
    directory.mkdir(parents=True, exist_ok=True)

    extension = allowed_types[content_type]
    filename = f"{uuid4().hex}{extension}"
    destination = directory / filename
    temporary = directory / f".{filename}.uploading"
    total_bytes = 0

    try:
        # Exclusive creation prevents accidentally overwriting a file.
        with temporary.open("xb") as output:
            while True:
                chunk = await upload.read(CHUNK_SIZE)

                if not chunk:
                    break

                total_bytes += len(chunk)

                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File exceeds the size limit of "
                            f"{max_bytes // (1024 * 1024)} MB."
                        ),
                    )

                output.write(chunk)

        if total_bytes == 0:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        # Check the file signature; MIME type alone is not sufficient.
        with temporary.open("rb") as saved_file:
            header = saved_file.read(16)

        if not _signature_matches(content_type, header):
            raise HTTPException(
                status_code=415,
                detail=(
                    "The file content does not match "
                    "its declared type."
                ),
            )

        os.replace(temporary, destination)

        return {
            "filename": filename,
            "media_type": media_type,
            "content_type": content_type,
            "size_bytes": total_bytes,
            "path": f"{listing_id}/{filename}",
        }

    finally:
        if temporary.exists():
            temporary.unlink()

        await upload.close()


def _signature_matches(
    content_type: str,
    header: bytes,
) -> bool:
    """Perform basic signature checks for supported formats."""
    if content_type == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")

    if content_type == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")

    if content_type == "image/webp":
        return (
            len(header) >= 12
            and header[:4] == b"RIFF"
            and header[8:12] == b"WEBP"
        )

    if content_type == "video/mp4":
        return len(header) >= 8 and header[4:8] == b"ftyp"

    if content_type == "video/webm":
        return header.startswith(b"\x1a\x45\xdf\xa3")

    return False
