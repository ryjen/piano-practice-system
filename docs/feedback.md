# Explicit, local feedback approvals

The player reports observations, not automated diagnostic conclusions. The planner remains read-only and consumes **only approved** entries.

## Procedure

1. Run a proposed session and optionally record a private MIDI take.
2. Decide on the manual `passed` self-report using the session's self-check, rather than merely copying the MIDI assessor's pass flag. Use `unknown` when no meaningful check was completed.
3. Run `pianoctl feedback propose` with a unique kebab-case ID, local practice date, exercise ID, difficulty, comfort, the manual passed result, and actual tempo. Optionally reference a private file under `local/` with `--evidence-ref`.
4. Review the proposed event JSON and its state revision. No file is changed by this command.
5. Approve with `pianoctl feedback apply <proposal> --state <private-state> --acknowledge <exact approval_key>`. This is the only intentional write path.
6. Generate the next session with `pianoctl plan --date <date> --state <private-state>`.

## Failure handling

- A malformed proposal, altered content, wrong key, unknown exercise, duplicate/conflicting ID, missing file, or stale state revision fails without applying.
- Reapplying an identical already-approved proposal reports `already-applied` without incrementing revision.
- The write uses a POSIX `flock` sibling lock, a same-directory temporary file, `fsync`, `0600` permissions, and an atomic `os.replace`. Other tools manually modifying the same state without the lock are outside its concurrency guarantee.
- The acknowledged SHA-256 content digest is **not a signature**; it demonstrates exact reviewed-byte intent only. There are no accounts, signatures, or trusted identities.
- Do not publish `local/` state or raw keyboard captures. All public fixtures remain synthetic.
- An approved feedback record is not a formal `maintained` or `reliable-context` promotion. Dedicated competency assessment and maintenance rules remain separate future work.

## Deliberate limitations

This version is POSIX-only due to `fcntl.flock`. It is a single-user reference implementation, not a hosted service or distributed database. MIDI timing and velocity cannot prove physical comfort or fingering. A `passed: true` result is explicitly attributed to the player. The pipeline does not silently import automatic assessment results as self-report.
