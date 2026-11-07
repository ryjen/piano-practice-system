# DAW and MIDI routing: REAPER or GarageBand

## Compatibility target

The planned sight-reading trainer must remain **DAW-agnostic**. The M-Audio
Oxygen Pro 61 is the MIDI input authority; a DAW is an optional local instrument
sound source, metronome, recording environment, or second observer. The trainer
should not need to query, control, automate, or record through the DAW to decide
whether a written note was played correctly.

| Environment | Intended DAW | MIDI stack | Status |
| --- | --- | --- | --- |
| Linux / NixOS | **REAPER** | ALSA MIDI input; optionally JACK/PipeWire routing after explicit qualification | Not physically tested |
| macOS | **GarageBand** | CoreMIDI USB input with Software Instrument track | Not physically tested |
| macOS (optional) | REAPER | CoreMIDI input | Not physically tested |

REAPER supports both Linux and macOS. GarageBand for Mac is a macOS
application; do not design a Linux GarageBand path.

## Minimum usable setup

### REAPER (Linux; optionally macOS)

1. Connect the Oxygen Pro 61; enumerate its **musical keyboard MIDI input**
   rather than assuming the control/DAW port carries notes.
2. In REAPER, open **Options → Preferences → Audio → MIDI Devices** and enable
   the appropriate MIDI input. Avoid enabling *control messages* unnecessarily;
   those are for controller surfaces, not ordinary piano note entry.
3. Create a track with a software instrument; select **Input: MIDI → [keyboard
   device/channel]**. Enable input monitoring and arm or set the track for
   monitor-only operation if you do not wish to record the session.
4. Play C4 and C5, then sustain pedal down/up. Independently inspect received
   MIDI pitches/channel and CC64 state. Confirm no doubled notes or stuck
   releases, and that key/octave shifts agree with the reading trainer.
5. For simultaneous DAW audio and trainer note feedback, first establish a
   working **single consumer** of each MIDI port, then separately verify
   whether the host's ALSA/JACK/PipeWire path can deliver events to both.
   Do **not** assume opening a physical ALSA MIDI port from two clients works.
   Choose a reviewed virtual-routing/forwarder plan before changing host
   services, firewall, realtime/audio settings, or device permissions.

Official reference: [REAPER User Guide](https://www.reaper.fm/userguide.php).

### GarageBand (Mac)

1. Connect the keyboard by USB. Verify it is recognized by macOS MIDI
   infrastructure; choose the **music note** port if multiple endpoints appear.
2. In GarageBand, create a **Software Instrument** track and choose a simple
   piano patch. Play and verify audible note-on/note-off plus octave range.
3. Record a short **MIDI** item only if desired, checking note identity and
   pedal behavior before treating the DAW as an independent observer.
4. Run the keyboard-reading trainer separately. Check concurrent MIDI
   access explicitly on that Mac; do not silently route software-instrument
   audio/MIDI into the trainer or require GarageBand automation.

Official reference: [GarageBand for Mac User Guide](https://support.apple.com/guide/garageband/welcome/mac).

## Architecture boundary

```text
                  +--> Reading trainer: staff display -> note judgment
Oxygen Pro 61 MIDI|
                  +--> optional DAW: REAPER or GarageBand -> instrument/audio
```

The split arrows are a **desired** architecture, not evidence of verified
multi-client MIDI routing. The app should accept a single selected physical
or authorized virtual port. Any duplication/bridging is a separately tested
OS-level capability, not an implicit property of MIDI.

The DAW must **not** be a hidden correctness oracle. If an instrument plays
the expected pitch because of a transposition/scale filter, the reading trainer
should still judge the raw selected MIDI note number, with intentional
transpositions explicitly calibrated and documented.

## Acceptance matrix (issue #2, physical hardware gate)

Verify on each chosen platform/DAW pair, capturing only redacted results:

- Same chosen note input port, exact note number C4/MIDI 60 and C5/MIDI 72
  under the project's declared convention; note-off and velocity-zero note-on;
- musical vs DAW-control endpoint differentiation, channel, octave/transpose
  and keyboard reset behavior, and sustain CC64 down/up;
- one-note and two-hand simultaneous chord/scale entries; no duplicate,
  missing or stuck events after disconnect/reconnect;
- note recognition without DAW running, DAW-only monitoring, then both
  simultaneously **if supported**; no unexpected port contention or echo;
- audible monitoring/latency acceptable to the player; MIDI event timestamps
  distinguished from audio rendering latency;
- results labeled separately for REAPER/Linux and GarageBand/macOS, with
  untested cases still **unverified**.

Neither the current CI environment nor the connected Desktop Commander
container has the physical Oxygen Pro 61 mapped. No device acceptance is
claimed, and no automatic DAW setup, subscriptions, recording or host routing
changes are authorized by this documentation.
