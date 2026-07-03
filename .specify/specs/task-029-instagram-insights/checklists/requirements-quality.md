# Requirements Quality Checklist: Instagram Graph API Insights Integration

**Purpose**: Validate completeness, clarity, consistency, and measurability of TASK-029 requirements  
**Created**: 2026-06-30  
**Depth**: Standard  
**Focus**: API integration, caching strategy, error handling, on-demand analytics  
**Audience**: PR Reviewer

---

## Requirement Completeness

- [ ] CHK001 - Are all account-level metrics explicitly listed (impressions, reach, profile_views, follower_count)? [Completeness, Spec §FR-001]
- [ ] CHK002 - Are all media-level metrics explicitly listed (engagement, impressions, reach, saved, likes, comments)? [Completeness, Spec §FR-003]
- [ ] CHK003 - Are cache invalidation triggers fully specified (time expiry + post publish)? [Completeness, Spec §FR-004, FR-006a]
- [ ] CHK004 - Are error response formats specified for all API failure modes (token expired, rate limit, 404, empty response)? [Completeness, Spec §Edge Cases]
- [ ] CHK005 - Are requirements defined for what happens when the user has multiple Instagram accounts? [Completeness, Spec §Edge Cases]
- [ ] CHK006 - Are loading state requirements defined for both account-level and media-level analytics? [Completeness, Spec §FR-013]

## Requirement Clarity

- [ ] CHK007 - Is "up to 1 hour" cache TTL precisely defined (exact TTL value or range)? [Clarity, Spec §FR-004, FR-005]
- [ ] CHK008 - Is "on-demand" clearly defined for media insights (triggered by user click, not automatic)? [Clarity, Spec §FR-003]
- [ ] CHK009 - Is "user-friendly error message" defined with specific text or pattern for each error type? [Clarity, Spec §FR-009]
- [ ] CHK010 - Is "sanitized data structure" defined with specific field names and types for media metrics? [Clarity, Spec §FR-010]
- [ ] CHK011 - Is the distinction between "account-level" and "media-level" insights clearly documented with examples? [Clarity, Spec §FR-001, FR-003]

## Requirement Consistency

- [ ] CHK012 - Are cache TTL values consistent between FR-004 (account), FR-005 (media), and SC-001/SC-002 timing requirements? [Consistency]
- [ ] CHK013 - Is token error handling consistent between FR-007 (insights) and TASK-028's existing token error detection? [Consistency, Spec §FR-007]
- [ ] CHK014 - Are error messages consistent across all failure paths (token expired, rate limit, fetch failure, no data)? [Consistency, Spec §Edge Cases]
- [ ] CHK015 - Is the "Inactiva" account state behavior consistent between FR-008 and TASK-028's account deactivation flow? [Consistency, Spec §FR-008]

## Acceptance Criteria Quality (Measurability)

- [ ] CHK016 - Can SC-001 ("2 seconds from cache, 5 seconds from API") be objectively measured in a test environment? [Measurability, Spec §SC-001]
- [ ] CHK017 - Can SC-002 ("3 seconds from cache, 5 seconds from API") be objectively measured for on-demand media insights? [Measurability, Spec §SC-002]
- [ ] CHK018 - Can SC-003 ("no more than 1 account insights fetch per account per hour") be verified through logging or monitoring? [Measurability, Spec §SC-003]
- [ ] CHK019 - Can SC-004 ("deactivation within 5 seconds") be measured end-to-end from API error to database update? [Measurability, Spec §SC-004]
- [ ] CHK020 - Is SC-005 ("without encountering unhandled errors or blank data") specific enough to be tested? [Measurability, Spec §SC-005]

## Scenario Coverage

- [ ] CHK021 - Are requirements defined for the case where the user's Instagram account is deleted from Instagram but still exists in our database? [Coverage, Gap]
- [x] CHK022 - Are requirements specified for what happens when the user clicks on multiple posts rapidly (concurrent on-demand requests)? [Coverage, Spec §Edge Cases] ✅ Resolved: reuses in-flight request
- [x] CHK023 - Are requirements defined for the case where cached data exists but the API returns different values (cache staleness indicator)? [Coverage, Spec §FR-006b, FR-013] ✅ Resolved: "Refreshing..." indicator + stale fallback
- [x] CHK024 - Are requirements specified for what happens when the Instagram API returns a 500 server error? [Coverage, Spec §Edge Cases] ✅ Resolved: transient failure handling
- [x] CHK025 - Are requirements defined for the case where the user's token permissions are downgraded (e.g., loses insights permission)? [Coverage, Spec §Edge Cases] ✅ Resolved: permission error detection + reconnect prompt

## Edge Case Coverage

- [ ] CHK026 - Is fallback behavior defined when the Instagram API rate limit is reached and no cached data exists? [Edge Case, Spec §Edge Cases]
- [ ] CHK027 - Are requirements specified for the case where a media ID exists but returns empty metrics? [Edge Case, Spec §Edge Cases]
- [ ] CHK028 - Is behavior defined when the user's account has zero followers (edge case for follower_count metric)? [Edge Case, Gap]
- [ ] CHK029 - Are requirements defined for the case where the Instagram API response is malformed or missing expected fields? [Edge Case, Gap]
- [x] CHK030 - Is the "Retry" button behavior fully specified (what happens when clicked, how many retries allowed)? [Edge Case, Spec §Edge Cases] ✅ Resolved: fresh fetch + loading + no retry limit

## Non-Functional Requirements

- [ ] CHK031 - Are performance requirements defined for concurrent users fetching analytics simultaneously? [NFR, Gap]
- [x] CHK032 - Are Redis cache key naming conventions documented to prevent collisions between accounts? [NFR, Spec §Assumptions] ✅ Resolved: namespaced by account ID
- [x] CHK033 - Are logging requirements specified for API calls, cache hits/misses, and errors? [NFR, Spec §FR-014] ✅ Resolved: FR-014 added
- [ ] CHK034 - Are security requirements defined for protecting access tokens during API calls? [NFR, Gap]

## Dependencies & Assumptions

- [ ] CHK035 - Is the assumption that `instagram_business_manage_insights` permission is already granted validated? [Assumption, Spec §Assumptions]
- [ ] CHK036 - Are dependencies on TASK-028's token error handling explicitly documented (shared code, shared error patterns)? [Dependency, Spec §Assumptions]
- [ ] CHK037 - Is the assumption about Redis availability validated for all deployment environments? [Assumption, Spec §Assumptions]
- [ ] CHK038 - Are the Instagram Graph API rate limits documented with official Meta API references? [Dependency, Spec §Assumptions]

## Ambiguities & Conflicts

- [x] CHK039 - Is there a conflict between FR-006 (return cached data) and FR-013 (display loading state) when cached data exists but is being refreshed? [Resolved by FR-006b] ✅ Resolved: FR-006b clarifies "Refreshing..." indicator for expired cache
- [x] CHK040 - Does "on-demand" in FR-003 mean the API is called every time, or only when cache is expired? [Resolved by FR-003 update] ✅ Resolved: FR-003 now explicitly states cache is respected
- [ ] CHK041 - Is the relationship between account-level cache invalidation (FR-006a) and media-level cache (FR-005) clearly defined? [Ambiguity]

## Notes

### Resolved in this pass (9 items):
- **CHK022**: Concurrent on-demand requests — edge case added (reuses in-flight request)
- **CHK023**: Cache staleness indicator — FR-006b clarifies "Refreshing..." behavior
- **CHK024**: 500 server error — edge case added (transient failure handling)
- **CHK025**: Token permission downgrade — edge case added (reconnect prompt)
- **CHK030**: Retry button behavior — edge case added (fresh fetch, no limit)
- **CHK032**: Redis cache key naming — assumption added (namespaced by account ID)
- **CHK033**: Logging requirements — FR-014 added
- **CHK039**: FR-006 vs FR-013 conflict — resolved by FR-006b (expired cache shows "Refreshing...")
- **CHK040**: On-demand vs cache — FR-003 updated to explicitly state cache is respected

### Remaining gaps (10 items):
- **CHK021**: Account deleted from Instagram but exists in DB — low impact, can be deferred to planning
- **CHK026**: Rate limit + no cached data — covered by FR-009 but could be more specific
- **CHK027**: Media ID exists but empty metrics — covered by "displays zeros" edge case
- **CHK028**: Zero followers edge case — low impact, displays 0 naturally
- **CHK029**: Malformed API response — low impact, can be handled in implementation
- **CHK031**: Concurrent users performance — low impact for single-user dashboard
- **CHK034**: Token security during API calls — covered by existing HTTPS + token storage patterns
- **CHK035-038**: Assumption validation — deferred to planning phase
- **CHK041**: Account vs media cache invalidation relationship — minor, can be clarified in plan
