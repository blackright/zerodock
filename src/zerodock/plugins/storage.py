"""Ultra-lightweight local object storage mock simulator (.zerodock/buckets)."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Any


class StorageError(Exception):
    """Base error for local object storage operations."""


class BucketNotFoundError(StorageError, FileNotFoundError):
    """Raised when a requested bucket does not exist."""


class ObjectNotFoundError(StorageError, FileNotFoundError):
    """Raised when a requested object key does not exist in a bucket."""


class LocalStorageMock:
    """Simulate S3-like bucket/object storage on local disk."""

    def __init__(self, base_dir: Path = Path(".zerodock/buckets")) -> None:
        self.base_dir = Path(base_dir).resolve()

    def _bucket_path(self, bucket: str) -> Path:
        if not bucket or "/" in bucket or "\\" in bucket or bucket in (".", ".."):
            raise ValueError(f"Invalid bucket name: {bucket!r}")
        target = (self.base_dir / bucket).resolve()
        if not target.is_relative_to(self.base_dir):
            raise ValueError(f"Invalid bucket path: {bucket!r}")
        return target

    def _object_path(self, bucket: str, key: str) -> Path:
        if not key or key.startswith(("/", "\\")):
            raise ValueError(f"Invalid object key: {key!r}")
        bucket_dir = self._bucket_path(bucket)
        target = (bucket_dir / key).resolve()
        if not target.is_relative_to(bucket_dir) or target == bucket_dir:
            raise ValueError(f"Object key escapes bucket: {key!r}")
        return target

    def ensure_bucket(self, bucket: str) -> Path:
        """Create a bucket directory if it does not already exist."""
        bucket_dir = self._bucket_path(bucket)
        bucket_dir.mkdir(parents=True, exist_ok=True)
        return bucket_dir

    def put_object(self, bucket: str, key: str, body: bytes) -> dict[str, Any]:
        """Store bytes at `<base_dir>/<bucket>/<key>` and return object metadata."""
        if not isinstance(body, (bytes, bytearray)):
            raise TypeError("Object body must be bytes")
        data = bytes(body)
        target = self._object_path(bucket, key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        mime_type, _ = mimetypes.guess_type(target.name)
        return {
            "bucket": bucket,
            "key": key,
            "size": len(data),
            "etag": hashlib.sha256(data).hexdigest(),
            "content_type": mime_type or "application/octet-stream",
        }

    def get_object(self, bucket: str, key: str) -> bytes:
        """Retrieve exact object bytes from `<base_dir>/<bucket>/<key>`."""
        return bytes(self.get_object_with_metadata(bucket, key)["body"])

    def get_object_with_metadata(self, bucket: str, key: str) -> dict[str, Any]:
        """Retrieve exact object bytes along with MIME type, size, and ETag."""
        bucket_dir = self._bucket_path(bucket)
        if not bucket_dir.exists():
            raise BucketNotFoundError(f"Bucket not found: {bucket}")
        target = self._object_path(bucket, key)
        if not target.is_file():
            raise ObjectNotFoundError(f"Object not found: {bucket}/{key}")
        data = target.read_bytes()
        mime_type, _ = mimetypes.guess_type(target.name)
        return {
            "bucket": bucket,
            "key": key,
            "body": data,
            "size": len(data),
            "etag": hashlib.sha256(data).hexdigest(),
            "content_type": mime_type or "application/octet-stream",
        }

    def list_objects(self, bucket: str) -> list[str]:
        """List all object keys in `<base_dir>/<bucket>` sorted lexicographically."""
        bucket_dir = self._bucket_path(bucket)
        if not bucket_dir.exists():
            raise BucketNotFoundError(f"Bucket not found: {bucket}")
        return sorted(
            path.relative_to(bucket_dir).as_posix()
            for path in bucket_dir.rglob("*")
            if path.is_file()
        )
