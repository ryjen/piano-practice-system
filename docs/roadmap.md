# Roadmap and acceptance boundaries

## Implemented (software reference)

- Technique-first catalog with **nine focus areas** and 18 bounded exercises: staff reading, two-handed coordination, fourths/fifths, triads, minor/accidentals, four-note harmony, pulse, navigation, dynamics
- Alfred's Basic Adult Piano Course Levels 1 and 2 as method-book *references*, not reproduced content
- Recital *metadata* for Für Elise, Over the Rainbow, and Jacob's Ladder; arrangement and page progress unknown
- Explicit Tuesday/Thursday planning preference, injected-date deterministic technique rotation, 15/20/30-minute plans, five-block flow and five-minute fallback
- Original single-staff MusicXML reading/minor exercises; no copyrighted book content or arbitrary external song transcription
- Optional MIDI capture using mido/python-rtmidi, offline pitch/timing/release/relative-velocity assessment, human-required gate for reading and physical techniques
- Versioned `feedback/v1` compatibility and `feedback/v2` explicit isolation/musical-context observations with optional recital reference
- Explicit feedback approval and deterministic competency progression with state/content digests, stale-state and conflicting-event rejection, one-step review-only regression, replay idempotence, cooperative POSIX lock and atomic state replacement
- Distinct-day gate evidence, adverse-feedback reset, maintained-state scheduling with explicit due/recovery reasons
- MIDI trace inspection with synthetic positive/negative tests that **never** assert physical hardware qualification

## Remaining external acceptance — do not mark done without evidence

1. **Oxygen Pro 61 physical qualification (#2):** real USB/ALSA MIDI port, known key-to-note calibration, CC64, channel/octave behavior, disconnect and reconnect, and independent DAW view on actual hardware. The remote Desktop Commander container has **no /dev/snd**, so this must be run on the connected host/device.
2. **Independent PR review and exact-head CI:** qualify implementation commit, adjudicate all review findings, and merge only when required checks are green. After merge, verify `main` CI and code/docs reflect final state.

## Subsequent enhancements (not part of current milestone)

- True hands-together/dual-staff notation and synchronized metronome/DAW timing
- Context-specific score-reading assessments using user-authored evidence beyond the single-staff seed exercises
- More expressive voicings, key signatures, pedal semantics, modes and rhythm patterns
- Optional local playback UI and audio via an external synthesizer
- Calendar/iCalendar integration and explicit longer-term learning capacity limits
- Read-only repertoire section planning with private checkpoint IDs instead of copyrighted scores

## Non-goals

Hosted subscriptions, mandatory AI services, uploading private practice logs, automatic injury/fingering diagnosis, automatic mastery claims from MIDI, copyrighted Alfred reproductions, or unapproved remote device changes.
