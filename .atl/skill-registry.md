# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| When creating a GitHub issue, reporting a bug, or requesting a feature | issue-creation | C:\Users\JuanPa\.config\opencode\skills\issue-creation\SKILL.md |
| When creating a pull request, opening a PR, or preparing changes for review | branch-pr | C:\Users\JuanPa\.config\opencode\skills\branch-pr\SKILL.md |
| When user asks to create a new skill, add agent instructions, or document patterns for AI | skill-creator | C:\Users\JuanPa\.config\opencode\skills\skill-creator\SKILL.md |
| When writing Go tests, using teatest, or adding test coverage | go-testing | C:\Users\JuanPa\.config\opencode\skills\go-testing\SKILL.md |
| When user says "judgment day", "judgment-day", "review adversarial", "dual review", "doble review", "juzgar", "que lo juzguen" | judgment-day | C:\Users\JuanPa\.config\opencode\skills\judgment-day\SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### issue-creation
- Blank issues are disabled — MUST use a template (bug report or feature request)
- Every issue gets `status:needs-review` automatically on creation
- A maintainer MUST add `status:approved` before any PR can be opened
- Questions go to Discussions, NOT issues
- Search existing issues for duplicates before creating
- Bug reports require: description, steps to reproduce, expected vs actual behavior, OS/agent/shell
- Feature requests require: problem description, proposed solution, affected area

### branch-pr
- Every PR MUST link an approved issue — no exceptions (use Closes/Fixes/Resolves #N)
- Every PR MUST have exactly one `type:*` label (type:bug, type:feature, type:docs, etc.)
- Branch naming: `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)\/[a-z0-9._-]+$`
- Commit messages MUST match conventional commits: `^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9\._-]+\))?!?: .+`
- Run shellcheck on modified scripts before pushing
- PR body MUST contain: linked issue, PR type, summary, changes table, test plan, contributor checklist

### skill-creator
- Create a skill when: pattern is used repeatedly, project conventions differ from generic best practices, complex workflows need step-by-step
- DON'T create a skill when: documentation already exists, pattern is trivial, one-off task
- Skill structure: `skills/{skill-name}/SKILL.md`, optional `assets/`, optional `references/`
- Frontmatter required: name, description (with trigger), license (Apache-2.0), metadata.author, metadata.version
- Naming: generic=`{technology}`, project-specific=`{project}-{component}`, testing=`{project}-test-{component}`
- References/ should point to LOCAL files, not web URLs
- Add new skills to AGENTS.md after creation

### go-testing
- Pure functions → Table-driven tests with `tests := []struct{...}` and `t.Run(tt.name, func(t *testing.T){...})`
- Bubbletea TUI state changes → Test `Model.Update()` directly with `tea.KeyMsg{Type: tea.KeyEnter}`
- Full TUI flows → Use `teatest.NewTestModel(t, m)` and `tm.WaitFinished(t, teatest.WithDuration(time.Second))`
- Visual output → Golden file testing with `testdata/TestName.golden`
- Mock system info → Use `t.TempDir()` for isolated test directories
- File organization: `model_test.go`, `update_test.go`, `view_test.go`, `teatest_test.go`, `testdata/`

### judgment-day
- **ALWAYS resolve skills first** — read registry → match by code+task context → build `## Project Standards` block → inject into BOTH judges AND fix agent
- Launch TWO judges in parallel via `delegate` (async) — never sequential, never reveal each other
- Synthesize verdict: Confirmed (both found) → fix; Suspect A/B (one found) → triage; Contradiction → flag manually
- WARNING classification: `WARNING (real)` = normal user can trigger; `WARNING (theoretical)` = contrived scenario → report as INFO only
- Fix Agent is separate delegation — never use a judge as fixer
- After Fix Agent → re-launch both judges in parallel for re-judgment
- After 2 fix iterations → ASK user: "Continue iterating?" If NO → JUDGMENT: ESCALATED
- **MUST NOT** declare APPROVED until: Round 1 judges CLEAN, OR Round 2 judges confirm 0 CRITICALs + 0 real WARNINGs
- **MUST NOT** push/commit after fixes until re-judgment completes

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | ./AGENTS.md | Stack: FastAPI, SQLAlchemy 2.0 async, PostgreSQL, Celery+Redis, MinIO. UV package manager. Key patterns: AsyncSessionLocal for FastAPI, SyncSessionLocal for Celery, JWT auth with Argon2. Webhook: HMAC-SHA1 validation. |
| CLAUDE.md | Not found | — |
| .cursorrules | Not found | — |
| GEMINI.md | Not found | — |
| copilot-instructions.md | Not found | — |

Project convention file found: AGENTS.md defines stack conventions and key patterns.

---

*Registry generated: 2026-04-05*
*Mode: hybrid (available to delegators via file + engram)*
