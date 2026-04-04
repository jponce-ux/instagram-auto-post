# Object Storage Specification

## Purpose

S3-compatible object storage for file uploads with presigned URL generation for external API access.

**Status**: MODIFIED by spec-010-privacidad-minio. This spec reflects the updated requirements.

## Requirements

### Requirement: File Upload

The system MUST upload files to MinIO (S3-compatible) storage asynchronously.

The `StorageService.upload_file()` method SHALL accept a file and user_id, store at user-scoped path, and return the storage key.

(Previously: accepted only file, stored at flat paths)

#### Scenario: Successful upload

- GIVEN an authenticated user provides a valid file
- WHEN `upload_file(file, user_id)` is called
- THEN the file is stored in MinIO
- AND the key follows pattern `{user_id}/{uuid}.{ext}`
- AND a MediaFile record is created in the database

### Requirement: Presigned URL Generation

The system MUST generate presigned URLs for file access.

Presigned URLs SHALL expire after 600 seconds (10 minutes) by default.

(Previously: expired after 604800 seconds / 7 days)

#### Scenario: Generate short-lived URL

- GIVEN a valid storage key
- WHEN `get_presigned_url(key)` is called
- THEN a URL is returned with expiration of 600 seconds
- AND the URL includes valid S3 signature parameters

#### Scenario: URL expires

- GIVEN a presigned URL was generated
- WHEN more than 600 seconds have passed
- THEN accessing the URL returns HTTP 403 from MinIO

### Requirement: Tunnel Host Replacement

The system MUST use the configured tunnel host for presigned URLs.

When `MINIO_TUNNEL_HOST` is configured, URLs SHALL use this hostname instead of internal MinIO address.

(Previously: URLs always used internal MinIO endpoint)

#### Scenario: Tunnel host configured

- GIVEN `MINIO_TUNNEL_HOST=instagramjp.domain.com`
- WHEN a presigned URL is generated
- THEN the URL uses `instagramjp.domain.com` as hostname
- AND internal address is not exposed

#### Scenario: No tunnel host configured

- GIVEN `MINIO_TUNNEL_HOST` is empty
- WHEN a presigned URL is generated
- THEN the URL uses the internal endpoint

### Requirement: Private Bucket Policy

The MinIO bucket MUST NOT have public access enabled.

All access to files SHALL go through presigned URLs. No anonymous access is permitted.

(Previously: bucket allowed public access through presigned URLs with long expiration)

#### Scenario: Anonymous access denied

- GIVEN an unauthenticated request to MinIO
- WHEN no presigned signature is provided
- THEN MinIO returns HTTP 403 Forbidden
- AND file content is not exposed

### Requirement: Bucket Auto-Provisioning

The system MUST create the storage bucket on startup if it does not exist.

The `ensure_bucket_exists()` method SHALL check for bucket existence and create it with SSE-S3 encryption if enabled.

#### Scenario: Bucket does not exist

- GIVEN MinIO is running with valid credentials
- WHEN `ensure_bucket_exists()` is called
- THEN the bucket is created
- AND SSE-S3 encryption is configured if enabled