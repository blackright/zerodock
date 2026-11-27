"""ZeroDock built-in local cloud-mock plugins."""

from zerodock.plugins.storage import (
    BucketNotFoundError,
    LocalStorageMock,
    ObjectNotFoundError,
    StorageError,
)

__all__ = [
    "BucketNotFoundError",
    "LocalStorageMock",
    "ObjectNotFoundError",
    "StorageError",
]
