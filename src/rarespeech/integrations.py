"""Persistent local model integrations; dependency/model installation is explicit."""

import sys
import wave
from pathlib import Path


class InflectAdapter:
    def __init__(self, options):
        import torch

        torch.set_num_threads(options.get("threads", 2))
        torch.set_num_interop_threads(1)
        model_dir = Path(options["model_dir"]).resolve()
        sys.path.insert(0, str(model_dir))
        # The official standalone release includes inference.py and model weights.
        from inference import InflectTTS

        self.engine = InflectTTS(model_dir, device=options.get("device", "cpu"))

    def synthesize(self, text, output, seed):
        import numpy as np

        result = self.engine.synthesize(text, seed=seed, speed=1.0, variation=0.667)
        rate, audio = result if isinstance(result, tuple) else (self.engine.sample_rate, result)
        with wave.open(str(output), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


class PiperAdapter:
    def __init__(self, options):
        from piper.voice import PiperVoice

        self.engine = PiperVoice.load(options["model_path"], use_cuda=False)

    def synthesize(self, text, output, seed):
        # Piper does not expose a reproducible seed through this API.
        with wave.open(str(output), "wb") as f:
            self.engine.synthesize_wav(text, f)


class KokoroAdapter:
    def __init__(self, options):
        import torch
        from kokoro import KPipeline

        torch.set_num_threads(options.get("threads", 2))
        self.pipeline = KPipeline(lang_code=options.get("language", "a"), device="cpu")
        self.voice = options.get("voice", "af_heart")

    def synthesize(self, text, output, seed):
        import numpy as np
        import torch

        torch.manual_seed(seed)
        chunks = [
            audio.numpy() if hasattr(audio, "numpy") else audio
            for _, _, audio in self.pipeline(text, voice=self.voice)
        ]
        if not chunks:
            raise ValueError("Kokoro returned no audio")
        audio = np.concatenate(chunks)
        with wave.open(str(output), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(24000)
            f.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


class KokoroONNXAdapter:
    def __init__(self, options):
        import onnxruntime as ort
        from kokoro_onnx import Kokoro

        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = options.get("threads", 2)
        session_options.inter_op_num_threads = 1
        session = ort.InferenceSession(options["model_path"], session_options, providers=["CPUExecutionProvider"])
        self.engine = Kokoro.from_session(session, options["voices_path"])
        self.voice = options.get("voice", "af_heart")
        self.speed = options.get("speed", 1.0)
        self.language = options.get("language", "en-us")

    def synthesize(self, text, output, seed):
        import numpy as np

        audio, rate = self.engine.create(text, voice=self.voice, speed=self.speed, lang=self.language)
        with wave.open(str(output), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())


def inflect(options):
    return InflectAdapter(options)


def piper(options):
    return PiperAdapter(options)


def kokoro(options):
    return KokoroAdapter(options)


def kokoro_onnx(options):
    return KokoroONNXAdapter(options)
