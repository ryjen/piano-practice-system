# Roadmap

## Implemented reference slice

- Technique-first, six-exercise synthetic public catalog (3 focus areas × 2 levels)
- Explicit Tuesday/Thursday preference, deterministic date-injected plan proposal
- Conservative feedback-sensitive rotation and repeat at reduced tempo
- Five-block session plan, 5-minute fallback, readable self-check
- Bounded optional USB MIDI capture via mido/python-rtmidi
- Deterministic key event assessment (pitch, relative onset intervals, release pairing, optional relative velocity contrast)
- No hidden state mutation and no hosted requirements

## Next gates (not implemented)

1. **Physical device verification:** inspect actual port names/channels/octave behavior on the Oxygen Pro 61; prove Note On/Off/CC64 and disconnect/recovery on Linux.
2. **Explicit feedback capture:** a local event log and approval command with state revision checks, immutable records, and idempotent application.
3. **Independent assessment:** baseline vs verification take, explicit manual physical comfort and hand identity, repeatability across days, gate results with unknown as a first-class outcome.
4. **Musical progression:** chord voicings, hands-together coordination, pedal technique, ear training, intentional space, repertoire references, and portable MIDI/MusicXML exercises.
5. **Optional playable UI:** a local MIDI piano monitor, count-in/metronome with one clock, text/key visualization, optional audio through an external synth; avoid pretending browser timing is sample-accurate.
6. **Scheduling:** add iCalendar export and due/maintenance selection with independent approval, not automatic reminders or remote notifications.

## Non-goals

Hosted subscriptions, AI inference, voice/audio interpretation, automatic diagnosis of pain or fingering, implicit proficiency assumptions, committing private MIDI takes, autonomous progression mutations.
