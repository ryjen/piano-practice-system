"""Optional M-Audio / generic USB MIDI adapter; never uploads data."""
from __future__ import annotations

import time


def _require_mido():
    try:
        import mido
    except ImportError as exc:
        raise RuntimeError("MIDI capture requires: pip install -e '.[midi]'") from exc
    return mido


def input_ports() -> list[str]:
    return list(_require_mido().get_input_names())


def capture(port: str, seconds: float, exercise_id: str, bpm: int | None = None) -> dict:
    if not 1 <= seconds <= 300:
        raise ValueError("capture seconds must be between 1 and 300")
    if bpm is not None and (type(bpm) is not int or not 40 <= bpm <= 180):
        raise ValueError("bpm must be an integer from 40 to 180")
    mido = _require_mido()
    events = []
    with mido.open_input(port) as inp:
        start = time.monotonic()
        while time.monotonic() - start < seconds:
            for msg in inp.iter_pending():
                timestamp = int((time.monotonic() - start) * 1000)
                if msg.type in ("note_on", "note_off"):
                    events.append({
                        "t_ms": timestamp, "type": msg.type,
                        "channel": msg.channel, "note": msg.note,
                        "velocity": msg.velocity,
                    })
                elif msg.type == "control_change" and msg.control == 64:
                    events.append({
                        "t_ms": timestamp, "type": msg.type,
                        "channel": msg.channel, "control": 64,
                        "value": msg.value,
                    })
                if len(events) >= 100000:
                    raise ValueError("too many MIDI events; capture aborted")
            time.sleep(0.005)
    result = {
        "contract_version": "midi-take/v1",
        "exercise_id": exercise_id,
        "source": "local-usb-midi",
        "events": events,
    }
    if bpm is not None:
        result["bpm"] = bpm
    return result
