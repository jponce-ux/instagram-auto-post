# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## Artifact Store Mode

**Current mode**: `hybrid`

Every SDD artifact is saved to BOTH:
- **Engram**: `~/.engram/engram.db` (cross-session recovery, fast queries)
- **OpenSpec**: `openspec/changes/{change-name}/` (git-friendly, team-shareable)

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Creating a pull request, opening a PR, or preparing changes for review | branch-pr | C:\Users\JuanPa\.config\opencode\skills\branch-pr\SKILL.md |
| Writing Go tests, using teatest, or adding test coverage | go-testing | C:\Users\JuanPa\.config\opencode\skills\go-testing\SKILL.md |
| Creating a GitHub issue, reporting a bug, or requesting a feature | issue-creation | C:\Users\JuanPa\.config\opencode\skills\issue-creation\SKILL.md |
| judgment day, judgment-day, review adversarial, dual review, doble review, juzgar, que lo juzguen | judgment-day | C:\Users\JuanPa\.config\opencode\skills\judgment-day\SKILL.md |
| Creating a new skill, add agent instructions, or document patterns for AI | skill-creator | C:\Users\JuanPa\.config\opencode\skills\skill-creator\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### branch-pr
- Every PR MUST link an approved issue — no exceptions
- Every PR MUST have exactly one `type:*` label
- Branch names MUST match: `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)\/[a-z0-9._-]+$`
- Conventional commits REQUIRED: `type(scope): description` or `type: description`
- PR body MUST contain: `Closes #N` or `Fixes #N` or `Resolves #N`
- Type-to-label mapping: `feat` → `type:feature`, `fix` → `type:bug`, `docs` → `type:docs`, `refactor` → `type:refactor`, `chore|style|test|build|ci` → `type:chore`, `feat!|fix!` → `type:breaking-change`
- Run shellcheck on modified scripts before pushing
- Never add `Co-Authored-By` or AI attribution to commits

### go-testing
- Table-driven tests are the standard pattern for multiple test cases
- For Bubbletea TUI: test `Model.Update()` directly for state changes, use `teatest.NewTestModel()` for full flows
- Golden file testing: compare output against saved files in `testdata/`
- Mock system info via `SystemInfo` struct for controlled testing
- Run `go test ./...` for all tests, `go test -v` for verbose, `go test -update` to update golden files

### issue-creation
- Blank issues are DISABLED — MUST use Bug Report or Feature Request template
- Every issue gets `status:needs-review` automatically on creation
- Maintainer MUST add `status:approved` before any PR can be opened
- Questions go to Discussions, NOT issues
- Bug Report template auto-labels: `bug`, `status:needs-review`
- Feature Request template auto-labels: `enhancement`, `status:needs-review`

### judgment-day
- Launch TWO independent judges in PARALLEL (never sequential) — neither knows about the other
- Judges review same target independently using identical criteria
- Orchestrator synthesizes verdict: Confirmed (both found), Suspect (one found), Contradiction (disagree)
- WARNING classification: "Can a normal user trigger this?" YES → real (fix required), NO → theoretical (report only)
- Fix Agent applies ONLY confirmed issues — no scope creep
- APPROVED when: 0 confirmed CRITICALs + 0 confirmed real WARNINGs
- After 2 fix iterations, ASK user before continuing — never escalate automatically

### skill-creator
- Create skills when pattern is reused repeatedly and AI needs guidance
- SKILL.md structure: frontmatter (name, description with Trigger, license) + When to Use + Critical Patterns + Code Examples + Commands
- Naming: `{technology}` for generic, `{project}-{component}` for project-specific
- Use `assets/` for templates/schemas/examples, `references/` for links to LOCAL docs
- DO NOT add Keywords section; DO NOT use web URLs in references

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | C:\Users\JuanPa\.config\opencode\AGENTS.md | OpenCode user-level rules |
| openspec/config.yaml | openspec/config.yaml | SDD artifact store mode: hybrid |
| .specify/specs/ | .specify/specs/SPEC-*.md | Manual specs (pre-SDD workflow) |

### AGENTS.md Summary
- Never add "Co-Authored-By" or AI attribution to commits
- Never build after changes
- When asking a question, STOP and wait for response
- Never agree with user claims without verification
- Always propose alternatives with tradeoffs
- Engram protocol active: save decisions/bugs/patterns proactively

Read the convention files listed above for project-specific patterns and rules.