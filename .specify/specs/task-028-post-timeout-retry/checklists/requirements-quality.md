# Requirements Quality Checklist: Stalled Post Timeout, Retry, and Token Health Check

**Purpose**: Validate completeness, clarity, consistency, and measurability of TASK-028 requirements  
**Created**: 2026-06-19  
**Depth**: Standard  
**Focus**: State machine lifecycle, retry pipeline, token health, SSE real-time sync  
**Audience**: PR Reviewer

---

## Requirement Completeness

- [ ] CHK001 - Are the exact conditions for transitioning a post from "procesando" to "fallido" fully specified (timeout threshold, check interval, error message)? [Completeness, Spec §FR-001, §FR-002]
- [ ] CHK002 - Are the exact conditions for transitioning a post from "reintentando" to "fallido" fully specified (5-minute threshold, error message)? [Completeness, Spec §FR-001a]
- [ ] CHK003 - Are all retry endpoint validation checks documented (ownership, post state, account active status)? [Completeness, Spec §FR-006, FR-007, FR-008]
- [ ] CHK004 - Are error response formats specified for all retry endpoint failure modes (unauthorized, wrong state, inactive account, already processing)? [Completeness, Spec §FR-006 to FR-008]
- [ ] CHK005 - Are requirements defined for what happens when the periodic stalled post check itself fails (database error, Redis unavailable)? [Gap]
- [ ] CHK006 - Are requirements specified for the `processing_started_at` field lifecycle (when set, when cleared, default value)? [Completeness, Spec §FR-002a]

## Requirement Clarity

- [ ] CHK007 - Is "original high-quality image from MinIO" defined with sufficient specificity (which bucket, which key field, how retrieved)? [Clarity, Spec §FR-005]
- [ ] CHK008 - Is the distinction between token errors (codes 463, 467) and non-token errors (network timeout, rate limit) clearly defined with specific error patterns? [Clarity, Spec §FR-009, FR-010]
- [ ] CHK009 - Is "3 consecutive retry failures" defined — does "consecutive" mean across all time, or reset after a successful retry? [Clarity, Spec §FR-013]
- [ ] CHK010 - Is the retry endpoint URL path explicitly defined in the requirements? [Clarity, Spec §FR-005]
- [ ] CHK011 - Is "user-friendly message" in FR-011 defined with specific text or a message pattern? [Clarity, Spec §FR-011]

## Requirement Consistency

- [ ] CHK012 - Are timeout thresholds consistent between FR-001 (15 min), FR-001a (5 min), and success criteria SC-001/SC-001a? [Consistency]
- [ ] CHK013 - Is the SSE event publishing requirement (FR-003) consistent with the existing SSE event contract from TASK-027? [Consistency, Spec §FR-003]
- [ ] CHK014 - Are error messages consistent across all failure paths (timeout, token error, retry failure, inactive account)? [Consistency, Spec §Edge Cases]
- [ ] CHK015 - Is the retry authorization chain (post → ig_account → user) consistent with the existing auth model used in other endpoints? [Consistency, Spec §FR-006]

## Acceptance Criteria Quality (Measurability)

- [ ] CHK016 - Can SC-001 ("no post remains in procesando for longer than 16 minutes") be objectively measured in a test environment? [Measurability, Spec §SC-001]
- [ ] CHK017 - Can SC-001a ("no post remains in reintentando for longer than 6 minutes") be objectively measured? [Measurability, Spec §SC-001a]
- [ ] CHK018 - Can SC-002 ("dashboard reflects status within 5 seconds via SSE") be tested reliably under varying network conditions? [Measurability, Spec §SC-002]
- [ ] CHK019 - Can SC-003 ("original high-quality image verified by file size/hash") be tested without access to the original upload? [Measurability, Spec §SC-003]
- [ ] CHK020 - Can SC-004 ("account deactivation within 10 seconds") be objectively measured end-to-end? [Measurability, Spec §SC-004]
- [ ] CHK021 - Is SC-005 ("retry completes within same time bounds as fresh post") defined with a specific time threshold? [Measurability, Spec §SC-005]

## Scenario Coverage

- [ ] CHK022 - Are requirements defined for the case where a post is manually set to "procesando" by an admin (not via normal flow)? [Coverage, Gap]
- [ ] CHK023 - Are requirements specified for what happens when the user navigates away from the dashboard during a retry request? [Coverage, Gap]
- [ ] CHK024 - Are requirements defined for concurrent retry attempts on the same post from multiple browser tabs? [Coverage, Spec §Edge Cases]
- [ ] CHK025 - Are requirements specified for the case where the periodic check runs while a post is mid-transition (e.g., being updated by the worker)? [Coverage, Gap]
- [ ] CHK026 - Are requirements defined for what happens when `processing_started_at` is set but the post is no longer in "procesando" or "reintentando" state? [Coverage, Gap]

## Edge Case Coverage

- [ ] CHK027 - Is fallback behavior defined when the original MinIO file is corrupted (exists but unreadable) during retry? [Edge Case, Spec §Edge Cases]
- [ ] CHK028 - Are requirements specified for the case where the Instagram account is deleted between retry attempts? [Edge Case, Gap]
- [ ] CHK029 - Is behavior defined when the periodic stalled check finds posts with `processing_started_at` in the future (clock skew)? [Edge Case, Gap]
- [ ] CHK030 - Are requirements defined for the case where SSE event publication fails after a post transitions to "fallido"? [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK031 - Are performance requirements defined for the periodic stalled post check (max query time, max rows scanned)? [NFR, Gap]
- [ ] CHK032 - Are database migration requirements documented for the `processing_started_at` column (nullable, default value, index)? [NFR, Gap]
- [ ] CHK033 - Are retry rate limiting requirements defined (e.g., max retries per minute per user)? [NFR, Gap]

## Dependencies & Assumptions

- [ ] CHK034 - Is the assumption that "original image file remains available in MinIO" validated with a retention policy? [Assumption, Spec §Assumptions]
- [ ] CHK035 - Are dependencies on TASK-027's token expiry detection explicitly documented (shared code, shared error patterns)? [Dependency, Spec §Assumptions]
- [ ] CHK036 - Is the assumption about Celery Beat infrastructure validated for the new stalled post check task? [Assumption, Spec §Assumptions]
- [ ] CHK037 - Are the Instagram Graph API error codes 463 and 467 documented with their official Meta API descriptions? [Dependency, Spec §Assumptions]

## Ambiguities & Conflicts

- [ ] CHK038 - Is there a conflict between FR-005 (retry uses "original image from MinIO") and the existing `_process_post_sync()` flow (which copies to public bucket first)? [Ambiguity]
- [ ] CHK039 - Is the relationship between the retry endpoint and the existing post creation endpoint clearly defined (shared logic vs. separate path)? [Ambiguity, Spec §FR-005]
- [ ] CHK040 - Does "consecutive retry failures" in FR-013 refer to client-side button clicks or server-side task failures? [Ambiguity, Spec §FR-013]
