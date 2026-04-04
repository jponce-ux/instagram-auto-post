# Skill Registry (Hybrid Mode)

## Artifact Store Mode: HYBRID

Every SDD artifact saved to BOTH:
- engram.db (memory)
- openspec/changes/ (files)

## User Skills

| Trigger | Skill |
|---------|-------|
| Creating a PR | branch-pr |
| Go tests, teatest | go-testing |
| Creating GitHub issue | issue-creation |
| judgment day, review adversarial | judgment-day |
| Creating new AI skill | skill-creator |

## Project Conventions

- AGENTS.md: User-level rules (no Co-Authored-By, never build, verify claims)
- openspec/config.yaml: SDD hybrid mode config
- openspec/changes/: SDD specs location (CHANGED from .specify/)
- .specify/ DELETED - migrated to openspec/changes/

## SDD Git Workflow

Every SDD change MUST follow this Git workflow:

### Phase 0: Create Branch
```bash
git checkout main
git pull origin main
git checkout -b feat/XXX-change-name
```

### During Implementation
Work on the feature branch, commit incrementally if needed.

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