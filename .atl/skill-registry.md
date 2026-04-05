# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Creating a PR, preparing changes for review | branch-pr | ~/.config/opencode/skills/branch-pr/SKILL.md |
| Writing Go tests, using teatest, adding test coverage | go-testing | ~/.config/opencode/skills/go-testing/SKILL.md |
| Creating a GitHub issue, reporting a bug, requesting a feature | issue-creation | ~/.config/opencode/skills/issue-creation/SKILL.md |
| judgment day, review adversarial, dual review, doble review, juzgar, que lo juzguen | judgment-day | ~/.config/opencode/skills/judgment-day/SKILL.md |
| Creating a new skill, add agent instructions, document patterns for AI | skill-creator | ~/.config/opencode/skills/skill-creator/SKILL.md |
| When user invokes `/sdd-apply-all-pending` or wants to batch-apply multiple specs | sdd-apply-all-pending | ~/.config/opencode/skills/sdd-apply-all-pending/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### branch-pr
- Every PR MUST link an approved issue — no exceptions
- Every PR MUST have exactly one `type:*` label
- Branch names MUST match: `^(feat\|fix\|chore\|docs\|style\|refactor\|perf\|test\|build\|ci\|revert)/[a-z0-9._-]+$`
- Commit messages MUST match: `^(build\|chore\|ci\|docs\|feat\|fix\|perf\|refactor\|revert\|style\|test)(\([a-z0-9\._-]+\))?!?: .+`
- Run shellcheck on modified scripts before pushing
- PR body MUST contain: Closes/Fixes/Resolves #N, summary, changes table, test plan
- No `Co-Authored-By` trailers in commits

### go-testing
- Use table-driven tests for multiple test cases
- Test Model.Update() directly for Bubbletea state changes
- Use teatest.NewTestModel() for full TUI flow testing
- Use golden file testing for visual output comparison
- Test pure functions with table-driven, mock dependencies for side effects
- Use t.TempDir() for file operations in tests

### issue-creation
- Blank issues are disabled — MUST use a template (bug report or feature request)
- Every issue gets `status:needs-review` automatically on creation
- Maintainer MUST add `status:approved` before any PR can be opened
- Questions go to Discussions, not issues
- Bug reports require: pre-flight checks, description, steps to reproduce, expected/actual behavior, OS, client, shell
- Feature requests require: problem description, proposed solution, affected area

### judgment-day
- Launch TWO sub-agents in parallel (never sequential) — each receives same target, works independently
- Neither agent knows about the other — no cross-contamination
- Verdict synthesis by orchestrator (not sub-agent): Confirmed (both found) → fix immediately; Suspect (one found) → triage; Contradiction → flag for decision
- Classify WARNINGs: real (normal user can trigger) vs theoretical (requires contrived scenario) — theoretical reported as INFO, NOT fixed
- After Fix Agent: re-launch both judges in parallel for Round 2
- After 2 fix iterations with remaining issues → ASK user before continuing
- APPROVED after Round 1: 0 confirmed CRITICALs + 0 confirmed real WARNINGs (theoretical warnings and suggestions may remain)

### skill-creator
- Create skill when: pattern used repeatedly, project-specific conventions differ, complex workflows need guidance
- Don't create when: documentation exists, pattern is trivial, one-off task
- SKILL.md required — assets/ for templates/schemas, references/ for local doc links
- Name conventions: generic `{technology}`, project-specific `{project}-{component}`, workflow `{action}-{target}`
- references/ points to LOCAL files, not web URLs
- Frontmatter required: name, description (with trigger), license Apache-2.0, author, version
- Start with critical patterns, use tables for decision trees, keep code minimal

### sdd-apply-all-pending
- Discover specs from engram (`sdd/*/tasks`) and/or openspec (`openspec/changes/*/tasks.md`)
- Determine execution order: explicit dependencies → numeric prefix (spec-011 < spec-012) → alphabetical
- A spec is "pending" if: has proposal+spec+design+tasks, apply-progress incomplete, not archived
- Execute sequentially: sdd-apply → sdd-verify → (optional) sdd-archive
- On apply failure: STOP batch, report which spec failed
- On verification failure: ask user to continue or stop
- Show progress: `[2/5] Applying spec-xyz...`
- Persist batch state so interruption can resume

## Project Conventions

No project-level convention files found (AGENTS.md, .cursorrules, CLAUDE.md, GEMINI.md).

## SDD Git Workflow

Every SDD change MUST follow this Git workflow:

### Phase 0: Create Branch
```bash
git checkout main
git pull origin main
git checkout -b feat/XXX-change-name
```

### Phase Final: Commit and Archive
```bash
git add .
git commit -m "feat(XXX): brief description"
git push origin feat/XXX-change-name  # optional
git checkout main  # wait for PR review before merge
```

### Naming Convention
- Branch: `feat/XXX-short-name` (e.g., `feat/010-minio-security-privacy`)
- Commit: `feat(XXX): description` (e.g., `feat(010): implement MinIO security`)

## SDD Tasks Template

Every spec's tasks.md MUST include:
- **Phase 0**: Git branch creation
- **Phase N (last)**: Git commit

This ensures each change is isolated in its own branch and properly committed before archiving.