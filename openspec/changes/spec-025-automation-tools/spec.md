# Feature Spec: Automation Tools

**Feature Branch**: `feat/spec-025-automation-tools`
**Created**: 2026-07-26
**Status**: Draft
**Type**: Feature
**Input**: Set of tools to maintain account activity - "Automation" section in sidebar
**Source**: Manual input
**Depends On**: spec-012-publicacion-estados-post-logica, spec-023-app-sidebar-layout

## User Scenarios & Testing

### User Story 1 - Hashtag Collections (Priority: P1)

The user can create and manage collections of hashtags to reuse across posts.

**Why this priority**: Hashtags are essential for reach; reusing curated sets saves time.

**Independent Test**: User creates a hashtag collection and sees it available when creating posts.

**Acceptance Scenarios**:
1. **Given** a user is on the Automation view, **When** they create a new hashtag collection with a name and list of hashtags, **Then** the collection is saved and appears in their list
2. **Given** a user has hashtag collections, **When** they create a new post, **Then** they can select a collection to auto-populate hashtags in caption
3. **Given** a user has multiple collections, **When** they edit or delete one, **Then** changes persist and don't affect posts already published

### User Story 2 - Content Templates (Priority: P2)

The user can create reusable caption templates with placeholders for quick post creation.

**Why this priority**: Consistency and efficiency for recurring post types (promos, quotes, etc.).

**Independent Test**: User creates template and uses it to create a post with placeholder values filled.

**Acceptance Scenarios**:
1. **Given** a user is on the Automation view, **When** they create a template with text and `{{placeholder}}` syntax, **Then** the template is saved
2. **Given** a user uses a template when creating a post, **When** they fill in the placeholders, **Then** the final caption has values substituted
3. **Given** a user tries to post without filling required placeholders, **When** they submit, **Then** the system shows validation error

### User Story 3 - Recurring Schedule (Priority: P2)

The user can set up recurring post schedules (e.g., "every Monday at 9am").

**Why this priority**: Consistent posting cadence without manual scheduling each time.

**Independent Test**: User sets up recurring schedule and posts are auto-created on schedule.

**Acceptance Scenarios**:
1. **Given** a user is on the Automation view, **When** they create a recurring schedule (frequency, time, template), **Then** the system creates SCHEDULED posts automatically per the pattern
2. **Given** a user has a recurring schedule, **When** they pause it, **Then** no new posts are auto-created until resumed
3. **Given** a recurring schedule would create a post with no media, **When** the time arrives, **Then** the system skips that occurrence and logs warning

### User Story 4 - Best Times to Post (Priority: P3)

The system suggests optimal posting times based on past engagement data.

**Why this priority**: Maximize reach by posting when audience is most active.

**Independent Test**: User sees suggested times in the Automation view after sufficient data exists.

**Acceptance Scenarios**:
1. **Given** a user has published posts with engagement data, **When** they view Automation, **Then** the system shows suggested posting times derived from their analytics
2. **Given** a user has insufficient data (< 10 published posts), **When** they view Automation, **Then** they see "Not enough data yet" message
3. **Given** suggested times are shown, **When** user schedules a post, **Then** the time picker defaults to a suggested time slot

## Edge Cases

- **Hashtag collection empty**: Allow saving empty collections (user may add later)
- **Template placeholder not found in post form**: Show validation error, don't allow submission
- **Recurring schedule exceeds post limit**: Instagram has posting limits (~50 posts/day); warn user
- **Recurring schedule for inactive account**: Skip creation, mark schedule with warning

## Functional Requirements

- FR-001: The system MUST allow users to create, edit, and delete hashtag collections
- FR-002: The system MUST allow users to select a hashtag collection when creating posts
- FR-003: The system MUST substitute selected hashtag collection into post caption
- FR-004: The system MUST allow users to create, edit, and delete caption templates with `{{placeholder}}` syntax
- FR-005: The system MUST validate required placeholders are filled before post creation
- FR-006: The system MUST support recurring schedules with frequency (daily, weekly) and time
- FR-007: The system MUST auto-create SCHEDULED posts per recurring schedule pattern
- FR-008: The system MUST allow pausing and resuming recurring schedules
- FR-009: The system SHOULD suggest optimal posting times based on engagement analytics
- FR-010: The system MUST store all automation settings per user/account

## Key Entities

### HashtagCollection
| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| user_id | int | FK → users.id |
| name | str | Collection name |
| hashtags | str | Comma-separated hashtags |
| created_at | datetime | Creation timestamp |

### ContentTemplate
| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| user_id | int | FK → users.id |
| name | str | Template name |
| caption_template | str | Text with `{{placeholder}}` syntax |
| created_at | datetime | Creation timestamp |

### RecurringSchedule
| Field | Type | Description |
|-------|------|-------------|
| id | int | Primary key |
| user_id | int | FK → users.id |
| ig_account_id | int | FK → instagram_accounts.id |
| frequency | str | "daily", "weekly", "custom" |
| time_of_day | time | When to create post |
| day_of_week | int | 0-6 for weekly (optional) |
| template_id | int | FK → content_templates.id (nullable) |
| hashtag_collection_id | int | FK → hashtag_collections.id (nullable) |
| is_active | bool | Whether schedule is active |
| created_at | datetime | Creation timestamp |

## Design References

**Source**: User description - "Automation" section in sidebar
**Resources**: See `resources/` directory for reference designs

| Resource | Description | Relevant Stories |
|----------|-------------|-----------------|
| `resources/automation-view.png` | Automation tools dashboard mockup | US-1, US-2, US-3 |

## Success Criteria

1. User can create and manage hashtag collections
2. Hashtag collections are available when creating posts
3. User can create and manage caption templates with placeholders
4. Recurring schedules auto-create scheduled posts
5. Recurring schedules can be paused and resumed
6. Best times suggestions appear when sufficient data exists
7. All automation settings persist per user
