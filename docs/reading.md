# Reading-first practice: staff → piano keyboard → feedback

## Outcome and current boundary

**Primary objective:** make printed piano notation intelligible at the keyboard,
first for isolated notes, then for unfamiliar intervals and phrases, and finally
for two hands and pieces in the user's licensed Alfred books.

The existing watch note-guessing practice is useful recognition training. It
does not establish the faster **eye → hand → sound** response required for
reading unfamiliar music. The current repository can export fixed original
MusicXML exercises and assess MIDI takes offline. It **does not** currently
provide an interactive score display that waits for played notes.

### Start using the keyboard now

[Pianomi](https://pianomi.app/) is an existing browser-based option for
unfamiliar generated notation, note reading, and immediate MIDI-key feedback.
It supports USB MIDI on a compatible desktop browser and can start with small
treble/bass-clef exercises. The user may continue using PianGo to learn known
scores and reference fingerings; a tool that shows the answer key in advance
is not a reliable *independent* sight-reading test.

For USB MIDI in a browser, use a supported browser such as Chrome/Edge and
grant input permission deliberately. The Web MIDI API requires a secure context
and is not universally supported; do not request SysEx for note recognition.
[Web MIDI API](https://developer.mozilla.org/en-US/docs/Web/API/Web_MIDI_API).
Keep third-party privacy/retention and license claims separate from this
repository's local-first guarantees.

**Hardware qualification remains outstanding:** the development container has
no direct Oxygen Pro 61 USB/ALSA MIDI device mapping. External app compatibility
and in-browser MIDI permissions have not been physically verified here.

## Reading-first 20-minute session

The current `practice-config/v1` budget is unchanged (20 minutes total):

| Stage | Minutes | Reading-first practice |
| --- | ---: | --- |
| Prepare | 3 | 2 min unseen single-note reading, 1 min relaxed two-hand alignment |
| Baseline | 3 | Mix treble and bass notes, correct register, no note names shown |
| Isolation | 8 | Unfamiliar 2–4 bar phrases with intervals, ledger lines, accidentals |
| Musical context | 4 | Small section of the user's legitimate Alfred Level 1–2 score |
| Verification | 2 | Re-test weak notes on a *new* prompt; record self-report and comfort |

This is a **practice suggestion**, not a feature the planner automatically
runs and not a claim that the player has completed a reading test.

## Proposed live-MIDI vertical slice

Implement a separate local interactive reading mode, with a small,
versioned contract shared by the existing offline catalog:

1. **Display** an original, unfamiliar note on a legible musical staff.
   First cut: choose treble or bass, short octave-bounded ranges, no
   note-name or highlighted-key hints before the first attempt. Show staff
   lines, clef, ledger lines and key/accidental symbols correctly.
2. **Listen** only to a user-selected MIDI input port and channel, on explicit
   permission. For browser Web MIDI, use HTTPS or localhost, no SysEx and no
   MIDI output. For a local Python adapter, reuse the existing bounded
   note-on parser rather than inventing USB/ALSA integration.
3. **Evaluate** note-on velocity greater than zero as an answer. Compare
   exact MIDI pitch (including octave and accidental), never just pitch
   class. Classify a wrong key as wrong note, wrong octave or wrong
   accidental when enough context exists. Handle note-on velocity zero as
   note-off, duplicate events, chord press and disconnect robustly.
4. **Advance** on a correct answer, with a separate explicit "reveal/skip"
   action after mistakes. Use deterministic seeded generation so tests
   reproduce cases, but vary a genuine practice run to prevent memorizing
   a fixed sequence. The first attempt remains independently meaningful.
5. **Measure** attempts and per-pitch response latency, rather than a single
   game score. Distinguish recognition, locating the key, and sight-reading
   a rhythm. Do not infer fingering, posture or complete musical comprehension
   from successful MIDI input.
6. **Keep private** all practice events. Work without an external account or
   remote telemetry. Preserve approval semantics if writing `state/v1`;
   the live mode must not automatically mark competency as mastered.

### Scope expansion after the first cut

Move from single written pitches to intervals/steps/skips, treble/bass
mixed staves, key signatures and accidentals, then timed unfamiliar phrases,
grand-staff LH/RH events and reading ahead. Avoid copyrighted method-book
content in public fixtures. A user's own Alfred checkpoints can link
progress as metadata without transcribing the score.

### Acceptance tests

- Synthetic MIDI note-on, wrong-octave, wrong-accidental, zero-velocity
  release, repeated key, extra key, port disconnect and reattach;
- deterministic seed and fresh-prompt variation, no answer leaks before
  the first played attempt, correct enharmonic spelling vs sounding pitch;
- legible treble and bass rendering with ledger notes, correct phase of
  hint/reveal controls, keyboard-only accessible UI;
- local storage/privacy inspection and no unintended network requests;
- direct USB keyboard smoke test is **separate** from synthetic CI and
  remains blocked until the actual device is accessible.

The goal is *reading unfamiliar notation*, not rewarding memorized scales
or teaching which physical finger pressed the key. Human/teacher evaluation
remains authoritative for physical technique.
