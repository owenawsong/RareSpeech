from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def inspect_audio(path: Path) -> dict:
    """PCM WAV diagnostics. Flags are triage cues, never pronunciation verdicts."""
    with wave.open(str(path), "rb") as f:
        channels, width, rate, frames = f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getnframes()
        if width != 2 or channels not in (1, 2):
            raise ValueError("use mono/stereo 16-bit PCM WAV; convert other formats before importing")
        if frames > rate * 1200:
            raise ValueError("audio exceeds 20 minutes")
        raw = f.readframes(frames)
    if len(raw) != frames * channels * width:
        raise ValueError("truncated WAV payload")
    samples = [x[0] / 32768 for x in struct.iter_unpack("<h", raw)]
    mono = [sum(samples[i : i + channels]) / channels for i in range(0, len(samples), channels)]
    peak = max((abs(x) for x in samples), default=0)
    rms = math.sqrt(sum(x * x for x in samples) / len(samples)) if samples else 0
    clipped = sum(abs(x) >= 0.999 for x in samples) / len(samples) if samples else 0
    # Count silence in 20ms frames; avoid treating low-level individual samples as silence.
    block = max(1, rate // 50)
    longest, streak = 0, 0
    for i in range(0, len(mono), block):
        part = mono[i : i + block]
        quiet = math.sqrt(sum(x * x for x in part) / len(part)) < 0.001
        streak = streak + len(part) if quiet else 0
        longest = max(longest, streak)
    flags = []
    if not samples:
        flags.append("empty")
    elif rms < 0.0001:
        flags.append("near_silent")
    if clipped > 0.001:
        flags.append("clipping_candidate")
    if longest / rate > 2:
        flags.append("long_silence_candidate")
    bins = 96
    stride = max(1, len(mono) // bins)
    envelope = [
        round(max((abs(x) for x in mono[i : i + stride]), default=0), 4) for i in range(0, len(mono), stride)
    ][:bins]
    return {
        "seconds": frames / rate,
        "sample_rate": rate,
        "channels": channels,
        "peak": peak,
        "rms": rms,
        "clipped_fraction": clipped,
        "longest_silence_seconds": longest / rate,
        "flags": flags,
        "waveform": envelope,
    }
