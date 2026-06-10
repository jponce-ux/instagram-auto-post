---
ticket: TASK-026
phase: spec
model: qwen3.6-plus
generated: 2026-06-09
status: draft
---

# Feature Specification: Image Thumbnails and Lightbox Viewer

**Feature Branch**: `026-image-thumbnails-lightbox`  
**Created**: 2026-06-09  
**Status**: Draft  
**Input**: User description: "as an user of mi-app-instagram I should land at /dashboard/ facing a short loading time. The pictures of 'historial de publicaciones' (history) with the previous post mustn't be the same size as original picture. Those snapshot must be a resize copy of the real picture but they should work as anchor that point to the real picture (not need to be real HTML anchor <a/>). if the user clicks on one picture in a row of this table of content, a blanket will cover the whole screen view and the real full size picture will appear in the middle with rounded borders. When the user post a new picture in instagram thru mi-app-instagram that picture must be stored at minio as is already happening but at the same time a resize small copy of it should be stored with the *-thumbnail added to its name, so for each post in history table the picture loaded at each row is the *-thumbnail version and as metadata stored at the HTML attribute that fit the most."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Thumbnail Generation on Upload (Priority: P1)

When a user uploads a new image to publish on Instagram, the system automatically generates a smaller resized copy (thumbnail) alongside the original. Both versions are stored in the object storage. The thumbnail filename includes a `-thumbnail` suffix to distinguish it from the original.

**Why this priority**: Without thumbnails, the dashboard loads full-size images which causes slow page loads. This is the foundation for all other user-facing improvements.

**Independent Test**: Upload an image through the dashboard, verify that two files exist in storage — the original and a smaller `-thumbnail` version. The thumbnail should be significantly smaller in file size and dimensions.

**Acceptance Scenarios**:

1. **Given** a user uploads a 5MB JPEG image through the post form, **When** the upload completes, **Then** two files are stored: the original and a `-thumbnail` version that is under 200KB.
2. **Given** a user uploads a PNG image, **When** the upload completes, **Then** both original and `-thumbnail` versions are stored with correct file extensions.
3. **Given** a user uploads an image that is already smaller than the thumbnail target size, **When** the upload completes, **Then** both versions are still stored (thumbnail may be same size or slightly smaller).

---

### User Story 2 - Dashboard History Shows Thumbnails (Priority: P2)

When the user visits the dashboard, the "historial de publicaciones" (post history) table displays thumbnail versions of images instead of full-size originals. Each thumbnail row contains metadata pointing to the full-size image URL.

**Why this priority**: This directly addresses the slow loading time complaint. Thumbnails load faster, improving the user experience immediately.

**Independent Test**: Navigate to the dashboard with existing posts. Verify that each row in the history table shows a small thumbnail image, not the full-size version. The page should load noticeably faster than before.

**Acceptance Scenarios**:

1. **Given** the user has 10 posts in their history, **When** they open the dashboard, **Then** all 10 rows display thumbnail images and the page loads within 2 seconds.
2. **Given** a post has no associated image (text-only), **When** the history renders, **Then** that row shows a placeholder icon instead of a broken image.
3. **Given** the user views the history table, **When** they inspect the image element, **Then** the `src` attribute points to the thumbnail URL and a `data-full-url` attribute points to the original full-size image URL.

---

### User Story 3 - Lightbox Full-Size Viewer (Priority: P3)

When the user clicks on a thumbnail in the post history, a full-screen overlay (lightbox) appears displaying the original full-size image centered on screen with rounded borders. The overlay dims the rest of the page. The user can close the lightbox by clicking outside the image or pressing Escape.

**Why this priority**: Users need to see the full-size image for verification purposes. This completes the thumbnail-to-full-image interaction flow.

**Independent Test**: Click any thumbnail in the history table. Verify that a dark overlay covers the entire viewport, the full-size image appears centered with rounded corners, and clicking outside the image or pressing Escape closes the overlay.

**Acceptance Scenarios**:

1. **Given** the user is viewing the dashboard history, **When** they click a thumbnail image, **Then** a dark overlay covers the full screen and the original full-size image appears centered with rounded borders.
2. **Given** the lightbox is open, **When** the user clicks outside the image area, **Then** the lightbox closes and the dashboard returns to its previous state.
3. **Given** the lightbox is open, **When** the user presses the Escape key, **Then** the lightbox closes.
4. **Given** the lightbox is open, **When** the user clicks the full-size image itself, **Then** the lightbox remains open (clicking the image does not close it).

---

### Edge Cases

- **What happens when the thumbnail file is missing from storage?** The system falls back to displaying the full-size image with a warning logged.
- **How does the system handle very large images (e.g., 20MB+)?** The thumbnail generation still produces a reasonably sized thumbnail (target ~150-200px width).
- **What if the user uploads a non-image file?** The system rejects the upload with an error message (existing validation handles this).
- **How does the lightbox behave on mobile screens?** The full-size image scales to fit the viewport width while maintaining aspect ratio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST generate a resized thumbnail copy of every uploaded image at the time of upload.
- **FR-002**: System MUST store the thumbnail with a `-thumbnail` suffix appended to the original filename (before the extension).
- **FR-003**: System MUST store both the original image and the thumbnail in the same storage bucket.
- **FR-004**: The post history table MUST display thumbnail images instead of full-size originals.
- **FR-005**: Each thumbnail image element MUST include metadata (HTML data attribute) containing the URL of the corresponding full-size original image.
- **FR-006**: Clicking a thumbnail in the history MUST trigger a full-screen overlay (lightbox) displaying the original full-size image.
- **FR-007**: The lightbox image MUST be centered on screen with rounded borders.
- **FR-008**: The lightbox MUST dim/obscure the rest of the page content behind a dark overlay.
- **FR-009**: The lightbox MUST close when the user clicks outside the image area.
- **FR-010**: The lightbox MUST close when the user presses the Escape key.
- **FR-011**: If a thumbnail is unavailable, the system MUST gracefully fall back to displaying the full-size image.
- **FR-012**: Posts without associated images MUST display a placeholder icon in the history table.

### Key Entities

- **Image Thumbnail**: A resized, smaller copy of an original uploaded image. Identified by the `-thumbnail` suffix in its storage key. Used for fast rendering in list/table views.
- **Original Image**: The full-resolution image uploaded by the user. Used for Instagram publishing and lightbox viewing.
- **Post History Entry**: A row in the dashboard's publication history table. Contains a reference to both the thumbnail URL (for display) and the original URL (for lightbox viewing).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dashboard page load time decreases by at least 50% compared to loading full-size images in the history table.
- **SC-002**: Thumbnail images are at least 70% smaller in file size than their original counterparts.
- **SC-003**: Users can open and view any full-size image from the history within 1 second of clicking the thumbnail.
- **SC-004**: 100% of uploaded images have both an original and a thumbnail version stored after the upload completes.

## Assumptions

- The existing MinIO storage service will be used for both original and thumbnail files.
- Thumbnail dimensions will be approximately 150-200px width (maintaining aspect ratio).
- The existing post creation flow (upload → MinIO → Celery → Instagram) will be extended to include thumbnail generation without changing the core publishing logic.
- Users have modern browsers that support CSS overlays and JavaScript event handling.
- The lightbox will be implemented client-side (no additional server round-trips needed since the full-size URL is embedded as metadata).
