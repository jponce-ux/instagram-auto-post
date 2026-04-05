# Tasks: User Dashboard (spec-013-user-dashboard)

## Phase 0: Git Branch

- [x] 0.1 Create branch `feature/spec-013-user-dashboard` from main

## Phase 1: Foundation

- [x] 1.1 Create `app/models/post.py` with Post model: id, user_id, media_file_id, caption, status, created_at, updated_at
- [x] 1.2 Modify `app/models/__init__.py` to export Post model
- [x] 1.3 Create `migrations/versions/add_posts_table.py` with Alembic migration for posts table (nullable fields)

## Phase 2: Core Implementation

- [x] 2.1 Create `app/dashboard/__init__.py` with module init
- [x] 2.2 Create `app/dashboard/service.py` with business logic: `get_user_accounts()`, `create_post()`, `get_user_posts()`
- [x] 2.3 Create `app/dashboard/routes.py` with protected routes: GET /dashboard, GET /dashboard/accounts, GET /dashboard/posts/feed (HX-Request aware), POST /dashboard/post

## Phase 3: Integration

- [x] 3.1 Modify `app/main.py` to import and register dashboard router with prefix `/dashboard`
- [x] 3.2 Modify `app/templates/base.html` to add Tailwind CDN with pinned version + integrity hash and dashboard nav link

## Phase 4: UI Implementation

- [x] 4.1 Create `app/templates/dashboard/layout.html` extending base.html with Tailwind, mobile-first container
- [x] 4.2 Create `app/templates/dashboard/index.html` with three sections: accounts, post_form, history
- [x] 4.3 Create `app/templates/dashboard/accounts.html` with accounts list and OAuth button
- [x] 4.4 Create `app/templates/dashboard/accounts_partial.html` with HTMX fragment for linked accounts list
- [x] 4.5 Create `app/templates/dashboard/post_form.html` with image upload (File), caption (Form), HTMX submit
- [x] 4.6 Create `app/templates/components/post_form.html` with progressive upload component
- [x] 4.7 Create `app/templates/dashboard/history.html` with post history display
- [x] 4.8 Create `app/templates/dashboard/posts_feed.html` with HTMX fragment for polling (hx-trigger="every 10s")

## Phase 5: Verification

- [x] 5.1 Verify GET /dashboard returns 401 without JWT
- [x] 5.2 Verify GET /dashboard returns 200 with valid JWT
- [x] 5.3 Verify accounts section displays linked accounts or empty state
- [x] 5.4 Verify post form validates image required (or shows validation error)
- [x] 5.5 Verify history shows posts with status badges
- [x] 5.6 Verify HTMX polling triggers every 10s on history section

## Phase 6: Git Commit

- [x] 6.1 Stage all changes and commit with conventional message: `feat(dashboard): add user dashboard with HTMX and Tailwind`
- [x] 6.2 Push branch to remote
