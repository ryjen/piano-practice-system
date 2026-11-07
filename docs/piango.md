# Export exercises to PianGo

[PianGo](https://piango.app/) accepts MusicXML (`.musicxml`, `.xml`, `.mxl`)
and MIDI (`.mid`), including MusicXML finger-number annotations. This repository
exports original catalog exercises as **MusicXML 4.0** to preserve written pitch,
rhythm, accidentals, separate hand timelines, and optional reference fingering.
No PianGo API, automatic upload, account, or cloud integration is needed.

## Use with the M-Audio Oxygen Pro 61

From the repository root:

```sh
mkdir -p local
python3 -m piano_practice.cli export --target piango \
  --exercise reading-staff-steps \
  > local/reading-staff-steps.musicxml

# Optional, explicitly suggested right-hand finger numbers for supported drills:
python3 -m piano_practice.cli export --target piango \
  --exercise minor-harmonic --fingering-reference \
  > local/minor-harmonic-fingering.musicxml

# Two-handed coordination, with separate synchronized right/left parts:
python3 -m piano_practice.cli export --target piango \
  --exercise coordination-together \
  > local/coordination-together.musicxml
```

Then open https://piango.app/, use **Choose a file** (or drag and drop),
and select the generated `.musicxml`. To practice through the Oxygen Pro 61,
connect the keyboard over USB, choose PianGo's MIDI input in a Web MIDI capable
browser (Chrome/Edge), and verify the notes and keyboard octave setting. The
device has not yet been physically qualified by this project's own MIDI tests.

Use `pianoctl export --target piango --exercise EXERCISE_ID` after installing
the local package. Exercise IDs come from `catalogs/exercises.json`.

## Exact semantics and limits

- **All 18 current catalog exercises** can be exported. This is a transport
  representation of the public, authored drills, not a reproduction of a
  commercial method book or recital score.
- Normal exercises are written as sequential notes at the catalog BPM.
  `pulse-eighth` uses eighth notes, not incorrectly expanded quarter notes.
- `coordination-alternating` alternates rests/notes across separate RH/LH
  parts. `coordination-together` pairs LH/RH octave notes on the same beats.
  This explicit modeling applies **only** to these known catalog IDs; the
  generic `notes` array does not encode arbitrary simultaneity or finger
  identity.
- Author-defined pitch spellings preserve the sharp/flat exercise examples,
  harmonic minor G-sharp, and the named circle-of-fourths/fifths roots.
  Scores use a simple 4/4 representation with rest padding.
- By default **no finger numbers are pinned**; PianGo may suggest them.
  `--fingering-reference` writes *illustrative RH choices* only for
  `reading-staff-steps`, `navigation-steps`, `minor-natural`, and
  `minor-harmonic`. Other exercises remain unannotated. Reconsider
  suggestions for your hand size and articulation; they are not a prescription.
- PianGo's fingering and animated hands are **guidance**, not physical
  detection of which finger pressed a key. MIDI can check pitch and timing,
  not fingers, posture, reading comprehension, physical comfort, or actual
  hand identity.
- Import is a **manual local file action**. The exporter is deterministic,
  offline, read-only, and does not modify learner history. Practice progress
  still requires human-observed feedback and explicit approval.
- Import compatibility is based on PianGo's published MusicXML support and
  local XML contract tests; no actual browser import / device check has been
  performed by this repository. A screenshot or browser verification of the
  current PianGo build should be retained before claiming end-to-end QA.

The pre-existing `pianoctl notation --exercise ...` command is retained for
its original reading/minor exercises. `export --target piango` is a separate
format-specific surface and can also be opened in score editors such as MuseScore.

## References

- [PianGo website and supported imports](https://piango.app/)
- [PianGo for piano teachers — printed fingering retention and MIDI](https://piango.app/for-piano-teachers/)
- [Why MusicXML retains more than MIDI](https://piango.app/learn-piano-sheet-music/)
- [Local piano curriculum and licensed method-book boundary](curriculum.md)
- [Oxygen Pro 61 hardware validation](hardware/qualification.md)
