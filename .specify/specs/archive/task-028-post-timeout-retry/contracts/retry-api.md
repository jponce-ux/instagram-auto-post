# Contract: Retry Post API

## POST /dashboard/posts/{post_id}/retry

Retries a failed post by re-dispatching it to the Celery worker.

### Authorization
- Requires authenticated user (JWT cookie)
- User must own the post
- Post's Instagram account must be linked to the user

### Request
- Path parameter: `post_id` (integer)
- No request body

### Success Response
- Status: 200
- Content-Type: application/json
```json
{
  "success": true,
  "post": {
    "id": 1,
    "status": "processing",
    "error_message": null
  }
}
```

### Error Responses

**400 — Post not in failed state**
```json
{
  "error": "Post is not in a failed state. Current status: processing"
}
```

**400 — Account inactive**
```json
{
  "error": "Instagram account is inactive. Please reconnect your account."
}
```

**400 — Post already processing**
```json
{
  "error": "Post is already being processed."
}
```

**401 — Unauthorized**
```json
{
  "error": "Unauthorized"
}
```

**403 — Post not owned by user**
```json
{
  "error": "Post not found"
}
```

**404 — Post not found**
```json
{
  "error": "Post not found"
}
```
