# M-Audio Oxygen Pro 61 — local setup

The Oxygen Pro 61 has 61 velocity-sensitive semi-weighted keys with aftertouch, USB MIDI, assignable zones, Smart Chord/Smart Scale, an arpeggiator, pads, transport, a 5-pin MIDI output and a 1/4-inch sustain pedal input. It **sends MIDI**, so connect a software instrument/DAW (or external MIDI sound module) to hear notes. The initial CLI does not synthesize sound.

## Baseline

1. Connect the keyboard via USB, open a software piano instrument, and establish an audible path if desired.
2. Disable **Smart Chord**, **Smart Scale**, arpeggiator, Note Repeat and split/layer zones for a basic untransformed note assessment.
3. Keep octave/transposition at a known setting. Do **not** assume physical key labels or octave notation match MIDI note values.
4. Run `pianoctl ports` after `pip install -e '.[midi]'` and select the device's musical-note MIDI input explicitly. DAW/Mackie/HUI surface ports may carry unrelated controls.
5. Use `pianoctl capture --port '<exact port>' --exercise pulse-quarter --seconds 20 > local/take.json` and play C four times; inspect emitted `note` values. The lesson's canonical C4 is **MIDI 60**, regardless of whether a DAW calls it C3 or C4.
6. Release the last note before capture stops. `pianoctl assess local/take.json` checks pitches, relative spacing, and lifecycle; it does not grade body mechanics or listening quality.

If a sustain pedal is attached, confirm its polarity at power-up with the pedal **released**, per the M-Audio manual. The capture adapter records CC64 but the current assessor does not interpret sounding-note sustain duration; note-off still means physical key release. Disable the pedal for baseline finger drills.

## Hardware limitations

- USB MIDI has no authenticated proof of instrument identity: a spoofed/virtual port can submit the same events.
- Smart Chord and other transformations can produce extra/different notes and invalidate assessment; extra notes are rejected but their cause is not inferable.
- Timing reflects receive times in the local process, including OS/device scheduling jitter; it is not a sample-accurate DAW clock.
- Channel aftertouch is available on the device but is deliberately outside the v1 normalized take contract.
- Fingers, hands, posture, pain, articulation and acoustic volume cannot be reliably inferred from note-on/off/velocity.
- No recording or upload occurs unless you explicitly capture/redirect output.

Source: [M-Audio product information](https://www.m-audio.com/keyboard-controllers/oxygen-pro-61.html) and [M-Audio series user guide](https://cdn.inmusicbrands.com/m-audio/maudio_documentation/Oxygen%20Pro%20Series%20-%20User%20Guide%20-v1.1.pdf).
