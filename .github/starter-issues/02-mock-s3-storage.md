# [FEAT-010] Mock Local Object Storage (S3 / File System Adapter)

**Labels**: `good first issue`, `help wanted`, `enhancement`, `cloud-mock`

## 🎯 Task Summary
Add an ultra-lightweight local object storage mock simulator that allows serverless functions to read and write files to a simulated "S3 Bucket" using local disk storage in `.zerodock/buckets/`.

## 💡 Background & Architecture
Many serverless functions upload or download images, PDFs, or data blobs from AWS S3 or Google Cloud Storage. Instead of running heavy Docker containers like MinIO or LocalStack, ZeroDock can simulate an S3 bucket interface at the application layer:
- Buckets are represented as subdirectories inside `.zerodock/buckets/<bucket-name>/`.
- Files are stored as standard local files.
- Provides a mock S3 client class or simulated REST endpoint compatible with standard `boto3` or `s3fs`.

## 📋 Suggested Implementation Steps
1. Create `src/zerodock/plugins/storage.py`:
   - Implement `LocalStorageMock(base_dir: Path)` with methods:
     - `put_object(bucket: str, key: str, body: bytes) -> dict`
     - `get_object(bucket: str, key: str) -> bytes`
     - `list_objects(bucket: str) -> list[str]`
2. Add optional configuration support in `serverless-local.yaml`:
   ```yaml
   storage:
     buckets:
       - user-uploads
       - reports
   ```
3. Add unit test in `tests/unit/test_storage_mock.py` verifying put, get, and list operations.

## ✅ Acceptance Criteria
- [ ] Storing an object writes the file cleanly to `.zerodock/buckets/<bucket>/<key>`.
- [ ] Retrieving an object returns the exact original bytes and mime type.
- [ ] Clean error handling if a requested object or bucket does not exist.
- [ ] Unit tests pass with `pytest`.
