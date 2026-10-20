---
name: commit-message
description: Write a git commit message in the user's style — Conventional Commits, one lowercase line, body only when needed (always for breaking changes, security fixes, data migrations and reverts), no workflow labels, no AI attribution. Use whenever writing or proposing a commit message.
---

# Commit message

Write the message only. This skill doesn't stage, commit or amend. Return
the message in a code block, exactly as it should be committed.

## Subject line

- Conventional Commits 1.0.0
  (https://www.conventionalcommits.org/en/v1.0.0/):
  `<type>[optional scope]: <description>`.
- Types: `feat` (new functionality), `fix` (bug fix), or `docs`, `test`,
  `refactor`, `perf`, `build`, `ci`, `chore`, `style`, `revert` as
  appropriate.
- Scope: optional, the area of the codebase in parentheses. Use the
  scopes already in `git log` (e.g. `feat(eval): ...`); don't invent a new
  one when an existing one fits.
- Breaking changes: `!` before the colon (`feat(api)!: ...`).
- The description is a **short summary of what the change does** (its
  functionality): imperative ("add", not "added"), all lowercase, no
  trailing period, one line.

## Body

- **Default: no body.** Add one only if the change can't be understood
  without it.
- **Always add a body** for:
  - breaking changes: a `BREAKING CHANGE: <what breaks and what to do>`
    footer
  - security fixes: what was exposed and to whom
  - data migrations: what changes in the data, and whether it can be
    rolled back
  - reverts: which commit is reverted (hash) and why
- Keep the body short: plain lines or `-` bullets, wrapped at 72.

## Never

- Workflow labels: no subtask numbers or IDs (`S1`, `subtask 2`, `step
  3`), no "per plan", no verifier or review rounds. Someone reading
  `git log` should only see what changed.
- AI attribution: no `Co-authored-by` for an AI, no "Generated with
  Claude Code", no mention of Claude.
- Filler: "this commit", "I", "we", "now".
