from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


class CommandAdapter:
    def __init__(self, config):
        self.argv = config["argv"]
        if not isinstance(self.argv, list) or not self.argv or any(not isinstance(a, str) for a in self.argv):
            raise ValueError("argv must be a nonempty JSON array of strings")
        self.timeout = config.get("timeout", 180)

    def synthesize(self, text, output: Path, seed):
        text_file = output.with_name(output.name + ".input.txt")
        text_file.write_text(text, encoding="utf-8")
        # No shell, no interpolation of user text into executable code.
        replacements = {
            "{text}": text,
            "{text_file}": str(text_file),
            "{output}": str(output),
            "{seed}": str(seed),
        }
        argv = []
        for arg in self.argv:
            argv.append(re.sub(r"\{(?:text|text_file|output|seed)\}", lambda m: replacements[m[0]], arg))
        result = subprocess.run(
            argv,
            input=text,
            text=True,
            encoding="utf-8",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
            shell=False,
        )
        if result.returncode:
            # Child output may include environment secrets; never copy it into public artifacts.
            raise RuntimeError(
                f"adapter exited {result.returncode}; reproduce the command locally for details"
            )
        text_file.unlink(missing_ok=True)


class SpeechAPI:
    def __init__(self, config):
        self.config = config
        url = config["url"]
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.query:
            raise ValueError("speech URL must use HTTP(S), without credentials or query parameters")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("remote speech endpoints require HTTPS")

    def synthesize(self, text, output, seed):
        cfg = self.config
        parameters = cfg.get("parameters", {})
        if not isinstance(parameters, dict) or set(parameters) & {
            "input",
            "model",
            "voice",
            "response_format",
        }:
            raise ValueError("parameters cannot override input, model, voice or response format")
        payload = {
            "model": cfg["model"],
            "input": text,
            "voice": cfg.get("voice", "default"),
            "response_format": "wav",
            **parameters,
        }
        if cfg.get("seed_parameter"):
            if cfg["seed_parameter"] in ("input", "model", "voice", "response_format"):
                raise ValueError("invalid seed parameter")
            payload[cfg["seed_parameter"]] = seed
        headers = {"Content-Type": "application/json"}
        key_env = cfg.get("api_key_env")
        if key_env:
            key = os.environ.get(key_env)
            if not key:
                raise ValueError(f"missing environment variable {key_env}")
            headers["Authorization"] = "Bearer " + key
        req = urllib.request.Request(cfg["url"], json.dumps(payload).encode(), headers, method="POST")
        try:

            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None

            opener = urllib.request.build_opener(NoRedirect)
            with opener.open(req, timeout=cfg.get("timeout", 180)) as response:
                data = response.read(100_000_001)
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"speech endpoint returned HTTP {error.code}") from None
        if len(data) > 100_000_000:
            raise ValueError("audio response exceeds 100 MB")
        output.write_bytes(data)


def load_adapter(config):
    if config.get("type") == "command":
        return CommandAdapter(config)
    if config.get("type") == "openai-speech":
        return SpeechAPI(config)
    if config.get("type") == "python":
        module, name = config["factory"].split(":", 1)
        return getattr(importlib.import_module(module), name)(config.get("options", {}))
    raise ValueError("adapter type must be command, openai-speech, or python")


def public_config(config):
    # Reject inline credentials instead of accidentally serializing them later.
    def check(value):
        if isinstance(value, dict):
            for k, v in value.items():
                if (
                    any(part in k.lower() for part in ("password", "secret", "token", "api_key"))
                    and k != "api_key_env"
                ):
                    raise ValueError("put credentials in environment variables, not adapter config")
                check(v)
        elif isinstance(value, list):
            for item in value:
                check(item)

    check(config)
    # Paths/hostnames/commands can be private; publish an identity hash and declared model settings only.
    from .io import digest

    return {
        "type": config.get("type"),
        "config_hash": digest(config),
        "model": config.get("model"),
        "voice": config.get("voice"),
        "revision": config.get("revision"),
        "parameters": config.get("parameters", {}),
        "options": {
            k: v
            for k, v in config.get("options", {}).items()
            if k in {"threads", "device", "language", "voice", "speed", "variation"}
        },
        "seed_supported": bool(config.get("seed_parameter") or config.get("seed_supported", False)),
    }
