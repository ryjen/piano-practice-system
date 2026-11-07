# Physical Oxygen Pro 61 qualification — bounded evidence plan

**Status:** pending real USB-MIDI device access. The available remote Desktop Commander container has no `/dev/snd` and no USB device mapping. Synthetic checks are not physical qualification.

## Preparation

- Use a Linux session with direct ALSA/JACK/PipeWire MIDI access to the actual connected keyboard, not a sandbox without device access.
- Install optional `pip install -e '.[midi]'` in an environment able to enumerate the keyboard.
- Set keyboard to a neutral preset: disable Smart Chord, Smart Scale, Note Repeat, arpeggiator, and zones. Confirm default transpose and octave. Use the regular musical MIDI input port rather than transport/DAW control port.
- Place all captures under ignored `local/`. Do not publish raw personal takes.

## Repeatable physical checks

1. List `pianoctl ports`; record device/port label and distinguish it from DAW control surface ports.
2. Play a known key corresponding to MIDI **60**, then D (62), and release. Save a bounded capture with `pianoctl capture --port "<exact port>" --exercise navigation-steps --seconds 15 --bpm 60 > local/oxygen-notes.json`.
3. Run `pianoctl hardware local/oxygen-notes.json` and inspect `observed_pitches`, `note_on`, `note_off`, channels, and `trace_integrity`. An arbitrary note trace can pass integrity; verify the **expected** pitch mapping against the physical keys and the DAW MIDI monitor.
4. Connect a sustain pedal (or verify existing one): test CC64-on and CC64-off in a separate capture. Observe whether note-off still corresponds to key release; the current assessor does not infer acoustic sustain duration.
5. Deliberately change octave or transpose, capture one short take, verify the mismatch relative to expected MIDI note mapping, and restore defaults.
6. Test disconnect/reconnect and mid-take disconnect; errors must surface, and unmatched note-on events must not be counted as successful evidence.
7. Compare timing observations with an independent DAW MIDI view; record approximate buffering/jitter limits and whether the device exposes separate input ports.
8. Record the test date, firmware/OS information voluntarily, exact commands, checks, any false positives, and observed recovery behavior. Publish only redacted, synthetic-safe results.

## Acceptance boundary

`pianoctl hardware` produces a **trace integrity report**, never `physical_device_qualified: true`. Even a perfect synthetic MIDI file proves only that its contents are well-formed. Physical qualification requires a separate dated, human-verifiable local-device test result. Do not close [issue #2](https://github.com/ryjen/piano-practice-system/issues/2) until those checks have been executed.

A passed trace cannot establish physical key assignment, hand identity, motor technique, acoustic sound, or suitability of an arrangement. Failure on port enumeration can reflect container permissions rather than a broken keyboard.


The MIDI assessor rejects any negative or noninteger event timestamp, including
the first event. A structurally valid take is still only advisory evidence,
not physical Oxygen Pro 61 qualification.

## Selected DAW compatibility targets

The current expected DAWs are **REAPER** on Linux (or macOS) and
**GarageBand** on macOS. See [DAW and MIDI routing](../daw-routing.md)
for separate OS/DAW acceptance checklists and the independently verified
musical input port vs controller input port distinction. Neither DAW or
simultaneous DAW/trainer MIDI access is hardware-qualified yet.
