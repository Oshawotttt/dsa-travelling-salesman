---
name: loopeng-auto
description: Loop-engineering execution with auto-commit — takes an approved spec file from /loopeng-plan, then each subtask is built test-first, independently verified (objectiveness check, then one main verifier that keeps context across subtasks), documented and committed without pausing, then a final code review of the whole task. Run only when the user invokes /loopeng-auto.
argument-hint: <path to an approved spec file from /loopeng-plan>
disable-model-invocation: true
---

# Loop engineering: execute (auto-commit)

Spec file: $ARGUMENTS

## 0. Load the spec

- If no spec file is given, list the spec files in the repo's
  `docs/specs/` and ask which one to run. Don't plan here: if the user
  has no spec, tell them to run `/loopeng-plan <task>` first.
- Read the spec file. If its status is not `**Status:** approved`, stop
  and tell the user to approve it through `/loopeng-plan`.
- The spec is the source of truth. Its header names the repo and any md
  file to update. **The docs** are the repo's own context files
  (`README.md`, `CLAUDE.md`/`AGENTS.md`, `docs/*.md`, `docs/adr/`).

Invoking this skill is the user's explicit permission to create the
spec's feature branch and to commit, but only as described in steps 1 and
5: no pushing, no other git writes.

Two verifier agents and one skill are used:
- `objectiveness-verifier`: a fresh one checks every verification prompt
  is objective before it is sent on.
- `main-verifier`: one long-lived agent that reviews every subtask in
  turn and keeps the context of the whole task.
- `mattpocock-skills:code-review`: reviews the whole task at the end.

## 1. Set up

- Check `git status` and the current branch. If uncommitted changes exist
  that the spec doesn't list (other than the spec file), stop and ask.
- If any external blocker in the spec is still open, stop and ask.
- If the spec names a feature branch, create it and switch to it.
- Commit the spec file alone, by explicit path, with
  `docs(specs): add <task title in lowercase> spec`.
- Record the **base commit**: `git rev-parse HEAD` after the spec commit.
  The final review diffs against it.

## 2. Execute: one subtask at a time

- Track the subtasks in the task list. Run them in the order from
  "Dependencies and blockers". Never start a subtask before every subtask
  it is blocked by is committed.
- Work on one at a time: code + tests, then verification (step 3), then
  docs (step 4), then commit (step 5), then continue to the next subtask
  without pausing.
- Run the subtasks yourself, serially. Don't hand them to subagents.
- Build test-first: call the Skill tool with "mattpocock-skills:tdd" for
  each subtask. Test only at the subtask's seams. Every acceptance
  criterion needs a test (or command) that proves it.
- Run typechecking and single test files often while building. Run the
  full test suite once before sending the subtask to verification. Use
  the spec header's **Commands**.
- Follow each subtask's **Decisions**, and the spec's **Out of scope** and
  **Interfaces** exactly. If one turns out impossible or wrong, stop and
  flag it to the user; don't work around it.
- If a test fails on a shared or environmental resource (`EADDRINUSE`, a
  database lock, a "database already exists" error, a locked temp file),
  wait briefly and rerun. Don't change code to work around it. If it keeps
  failing, stop and flag it to the user.
- Keep a **Decisions made** list per subtask: every design decision the
  spec didn't dictate, one line each, the decision and why. Before step
  4, add each one to the subtask's doc deltas (or note why it needs no
  doc).
- Before verification, tick each acceptance criterion in the spec file
  that its test now proves. Leave unproved ones unticked.
- If the spec changes during implementation, update the spec file, say
  so, and add the change to the doc deltas.

## 3. Verify: objectiveness check, then the main verifier

Every verification prompt goes through two agents, in order:

1. **`objectiveness-verifier`** (`subagent_type: "objectiveness-verifier"`,
   a fresh one each time, `run_in_background: false`). Send it the exact
   prompt you intend to give the main verifier. It only judges whether
   the prompt is objective and returns **PASS** or **FAIL**.
   - **FAIL**: rewrite the prompt without the quoted lines and send it to
     a new objectiveness verifier. Nothing goes to the main verifier.
   - **PASS**: send that exact prompt, unchanged, to the main verifier.
2. **`main-verifier`** (`subagent_type: "main-verifier"`). Spawn it
   **once**, for the first subtask, and keep its agent ID. For every later
   round (re-verification or the next subtask), continue that same agent
   with `SendMessage` so it keeps the context of the whole task. Only
   spawn a replacement if it can no longer be reached, and say so in the
   final report.

The prompt contains **only** facts: the repo path, the subtask goal exactly
as approved, its acceptance criteria exactly as approved (unticked), the
subtask's Decisions, the spec's Interfaces entries that apply to this
subtask, the Out of scope list, all copied verbatim, the files changed,
the test commands from the spec header, and the relevant doc paths. **Never
include your reasoning, justifications, confidence, or "I think this is
correct."** That includes on re-verification: don't say what was fixed or
argue against earlier findings. The review has to be objective.

Main verifier verdicts:
- **PASS**: go to step 4.
- **FAIL**: apply the listed fixes, then re-verify (objectiveness check
  first, then the same main verifier).
- If you're certain a FAIL finding is not a bug, don't override the
  verifier. Stop and flag it to the user with evidence. Nothing gets
  committed until it's resolved.

Limits, counted separately per subtask:
- **3 objectiveness FAILs**: stop and flag it to the user with the latest
  objectiveness output. Don't send a 4th prompt.
- **3 main-verifier FAILs**: stop and flag it to the user with the main
  verifier's latest output. Don't run a 4th round and don't commit it.

## 4. Update docs (after PASS)

- Apply every doc delta for the subtask:
  - Decisions → an ADR in `docs/adr/`, one file per decision. An ADR is
    not a ticket or a task: no checklist, owner, subtask ID or status
    workflow. Write one only when the decision is all three: hard to
    reverse, surprising without context, and the result of a real
    trade-off. Record no other decision in any doc.
    - File: `docs/adr/NNNN-<slug>.md`, `NNNN` = highest existing number
      plus one (`0001` for the first). Create `docs/adr/` only when the
      first ADR is needed.
    - Body: `# <short title of the decision>`, then 1-3 sentences: the
      context, what was decided, and why. Add `## Considered options` or
      `## Consequences` only when they are worth remembering.
    - Check existing ADR titles first (`grep -m1 "^# " docs/adr/*.md`).
      Already recorded: write nothing. Replacing an old decision: write a
      new ADR and give the old one the frontmatter
      `status: superseded by ADR-NNNN`, leaving its text unchanged.
  - New or changed terms → the repo's glossary (`GLOSSARY.md`, or the
    right per-context one). Add only the term and a tight definition, in
    the glossary's existing format; no implementation detail.
  - Structure (modules, data flow, key seams) → `docs/ARCHITECTURE.md`.
    Structure only: decisions go in ADRs.
  - Interfaces between modules (function signatures, data shapes, DB
    schema, endpoint request/response) → `docs/CONTRACTS.md`.
  - Anything else → the matching doc file.
  - If a doc delta targets `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md` or
    `GLOSSARY.md` and the file is missing, create it with a `# <name>`
    heading and only what this delta adds. Don't fill it with anything
    beyond the delta. A glossary lists each term as `**Term**: definition`.
    Never create any other doc file unless the spec says so: put the
    delta in the most fitting existing doc instead.
  - Edit existing docs in place, in their existing structure and style;
    don't rewrite them.
  - If the spec names an md file to update, update it with codebase
    context (where things live, how they fit together, gotchas) for
    future reference.

## 5. Commit (only after PASS and docs)

- Stage **only** the files this subtask changed (code, tests, docs) plus
  the spec file (its ticked criteria), by explicit path. Never use
  `git add -A` or `git add .`. Check with `git status` /
  `git diff --cached --stat` that nothing unrelated is staged.
- Write every commit message by calling the Skill tool with
  "commit-message".
- Never use `--no-verify` or `--amend`, and never push. If a pre-commit
  hook fails, fix the cause, re-stage and make a new commit. If the fix
  touches code, re-verify first.
- Report the commit hash and message in one line, then move on to the
  next subtask.

## 6. Final verification: code review (after the last subtask)

Once every subtask is committed, review the whole task with the Skill tool:
`mattpocock-skills:code-review`. Give it the **base commit** from step 1 as
the fixed point and the **spec file** as the spec. Wait until both its
Standards and Spec reviews have reported before acting.

Act on the findings:
- **Spec findings** (missing, partial or wrong against the spec): every
  real defect must be fixed.
- **Standards findings**: judgement cues, not rules. Fix each one you agree
  improves the code without changing behaviour. List the rest, with a
  one-line reason each, for the report.
- If you're certain a Spec finding is not a bug, don't drop it. Stop and
  flag it to the user with evidence.

Fixes go through the normal loop: verify them (step 3, same main verifier,
objectiveness check first), update docs (step 4) and commit (step 5) as new
commits. Their messages weren't in the approved spec, so show them in the
report. Then run the code review again from the top of this step, still
against the base commit.

Limit: **3 code-review rounds with Spec defects**. After the 3rd, stop and
flag it to the user with the latest review output. Don't run a 4th round.

## 7. Report

- Give a summary: the spec file path, the commits made (hash + message,
  marking any not in the approved spec), per subtask the objectiveness
  FAILs and main-verifier rounds, the code-review rounds and the Standards
  findings not fixed (with reasons), and every doc delta applied and
  where.
- **Acceptance criteria**: each one, grouped by subtask, marked `met` or
  `not met`, with the test or command that proves it.
- **Decisions made**: every entry, grouped by subtask, and the ADR it was
  recorded in, or "no ADR" with which of the three ADR tests it fails.
- **Human checks**: end the report with the full checklist from the spec,
  ready for the user to run, with steps and expected results.
- Remind the user that nothing was pushed.
