# Skill Registry

**Delegator use only.** Any agent that launches sub-agents reads this registry to resolve compact rules, then injects them directly into sub-agent prompts. Sub-agents do NOT read this registry or individual SKILL.md files.

See `_shared/skill-resolver.md` for the full resolution protocol.

## User Skills

| Trigger | Skill | Path |
|---------|-------|------|
| Writing Go tests, using teatest, or adding test coverage | go-testing | C:/Users/JuanPa/.config/opencode/skills/go-testing/SKILL.md |
| Creating new AI skills | skill-creator | C:/Users/JuanPa/.config/opencode/skills/skill-creator/SKILL.md |
| Creating a pull request, opening a PR, or preparing changes for review | branch-pr | C:/Users/JuanPa/.config/opencode/skills/branch-pr/SKILL.md |
| Creating a GitHub issue, reporting a bug, or requesting a feature | issue-creation | C:/Users/JuanPa/.config/opencode/skills/issue-creation/SKILL.md |
| Parallel adversarial review with two judges | judgment-day | C:/Users/JuanPa/.config/opencode/skills/judgment-day/SKILL.md |

## Compact Rules

Pre-digested rules per skill. Delegators copy matching blocks into sub-agent prompts as `## Project Standards (auto-resolved)`.

### go-testing
- Use table-driven tests for multiple test cases with name, input, expected, wantErr fields
- Test Bubbletea models directly: call m.Update(msg) and assert on returned model
- Use teatest.NewTestModel(t, model) for full TUI integration tests with tm.Send() for key events
- Golden file testing: compare View() output against testdata/*.golden files
- Mock system dependencies via interface injection, use t.TempDir() for file operations

### skill-creator
- Create skills for reusable patterns, not one-off tasks or trivial patterns
- Structure: skills/{skill-name}/SKILL.md + optional assets/ and references/ directories
- Frontmatter required: name, description (includes Trigger:), license, metadata (author, version)
- Content: start with Critical Patterns, use tables for decision trees, keep examples minimal
- Register skill in AGENTS.md after creating: `| {skill-name} | {description} | [SKILL.md](skills/{skill-name}/SKILL.md) |`

### branch-pr
- Every PR MUST link an approved issue and have exactly one type:* label
- Branch naming: `type/description` where type is feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert
- Conventional commits: `type(scope): description` or `type: description`
- PR body MUST contain: Closes/Fixes/Resolves #N, PR type checkbox, summary (1-3 bullets), changes table, test plan
- Run shellcheck on modified scripts before pushing

### issue-creation
- Use Bug Report template for bugs, Feature Request template for features
- Every issue gets status:needs-review automatically; maintainer must add status:approved before PRs
- Required fields: Pre-flight Checks, Bug Description (or Problem Description for features), Steps to Reproduce (or Proposed Solution), Expected/Actual Behavior, OS/Agent/Shell dropdowns
- Questions go to Discussions, NOT issues

### judgment-day
- Launch TWO parallel blind judges via delegate(async) — never sequential, never self-review
- Classify WARNINGs as(real) vs (theoretical): can a normal user trigger it? YES → real, NO → theoretical
- Confirmed = found by BOTH judges; Suspect = found by one; Contradiction = judges disagree
- Fix only confirmed CRITICALs and real WARNINGs; theoretical = INFO, no fix
- After 2 fix iterations, ASK user before continuing; never auto-escalate

## Project Conventions

| File | Path | Notes |
|------|------|-------|
| AGENTS.md | C:/Users/JuanPa/.config/opencode/AGENTS.md | Global agent rules and engram protocol |
| .specify/specs/ | .specify/specs/SPEC-*.md | Project specification files in Spanish |

Read the convention files listed above for project-specific patterns and rules. All referenced paths have been extracted — no need to read index files to discover more.