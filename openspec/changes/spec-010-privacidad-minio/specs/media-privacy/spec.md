# Media Privacy Specification

## Purpose

User-scoped file storage with ownership validation and encrypted files. Ensures that media files are private by default and only accessible through authorized requests.

## Requirements

### Requirement: User-Scoped File Paths

The system MUST store all uploaded files with paths scoped to the owning user.

Files SHALL be stored using the pattern `{user_id}/{uuid}.{extension}` where `user_id` is the authenticated user's ID and `uuid` is a unique identifier.

#### Scenario: Upload file with user scope

- GIVEN a user is authenticated with ID `123`
- WHEN they upload `photo.jpg`
- THEN the file is stored at path `123/550e8400-e29b-41d4-a716-446655440000.jpg`
- AND no other user can access this file's path directly

#### Scenario: Anonymous upload denied

- GIVEN no authenticated user
- WHEN a file upload is attempted
- THEN the system returns HTTP 401 Unauthorized

### Requirement: Media Ownership Record

The system MUST create a database record for each uploaded file tracking ownership.

A `MediaFile` record SHALL be created with `key`, `user_id`, `original_filename`, and `content_type` fields.

#### Scenario: MediaFile record created on upload

- GIVEN an authenticated user uploads a file
- WHEN upload completes successfully
- THEN a MediaFile record exists with `user_id` matching the authenticated user
- AND `key` matches the storage path

### Requirement: Protected Media Access Endpoint

The system MUST provide a protected endpoint for retrieving presigned URLs.

The endpoint `GET /dashboard/media/{file_id}` SHALL return a presigned URL only after validating JWT authentication AND file ownership.

#### Scenario: Owner requests their own file

- GIVEN user with ID `123` owns file with ID `5`
- WHEN they request `GET /dashboard/media/5` with valid JWT
- THEN the system returns HTTP 200 with presigned URL
- AND URL expires in 600 seconds

#### Scenario: User requests another user's file

- GIVEN user with ID `123` does NOT own file with ID `6`
- WHEN they request `GET /dashboard/media/6` with valid JWT
- THEN the system returns HTTP 403 Forbidden

#### Scenario: Unauthenticated request

- GIVEN no JWT token is provided
- WHEN any file is requested
- THEN the system returns HTTP 401 Unauthorized

### Requirement: SSE-S3 Encryption

The system SHOULD encrypt stored files at rest using server-side encryption.

Files SHALL be encrypted with SSE-S3 when uploaded to MinIO, ensuring data protection even with direct disk access.

#### Scenario: File encrypted on upload

- GIVEN `MINIO_SSE_ENABLED=true`
- WHEN a file is uploaded
- THEN MinIO stores the file with AES-256 encryption
- AND the encryption is transparent to the application