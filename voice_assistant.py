"""Nova Voice: a CPU-friendly Windows voice assistant using local Ollama.

Requirements: Python 3.11, Ollama + nova-voice model, microphone and speakers.
Run: python voice_assistant.py
"""

from __future__ import annotations

import io
import os
import re
import sys
import time
import wave
from collections import deque

import numpy as np
import pyttsx3
import sounddevice as sd
from faster_whisper import WhisperModel
from ollama import Client


# Adjust these constants for your laptop and microphone.
OLLAMA_MODEL = "nova-voice"
WHISPER_MODEL = "tiny"  # Set to "base" for better Hindi accuracy (slower).
MIC_THRESHOLD = 0.012  # Lower if speech isn't detected; raise for noisy rooms.
SILENCE_SECONDS = 0.8
WAIT_FOR_SPEECH_SECONDS = 7.0
MAX_RECORD_SECONDS = 15.0
BLOCK_SECONDS = 0.2
MAX_HISTORY_MESSAGES = 6


def record_voice() -> tuple[np.ndarray | None, int | None]:
    """Record after the user presses Enter, stopping after a silent period."""
    device = sd.query_devices(kind="input")
    sample_rate = int(device["default_samplerate"])
    if sample_rate <= 0:
        sample_rate = 16000
    block_size = max(1, int(sample_rate * BLOCK_SECONDS))

    leading_audio: deque[np.ndarray] = deque(maxlen=3)
    chunks: list[np.ndarray] = []
    speech_started = False
    silent_blocks = 0
    silence_limit = max(1, round(SILENCE_SECONDS / BLOCK_SECONDS))

    print("Listening... speak now.")
    start_time = time.monotonic()

    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
        blocksize=block_size,
    ) as stream:
        while time.monotonic() - start_time < MAX_RECORD_SECONDS:
            frames, overflowed = stream.read(block_size)
            if overflowed:
                print("(Warning: microphone buffer overflow)")
            audio = frames[:, 0].copy()
            rms = float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))
            speaking = rms >= MIC_THRESHOLD

            if not speech_started:
                leading_audio.append(audio)
                if speaking:
                    speech_started = True
                    print("Speech detected...")
                    chunks.extend(leading_audio)
                    leading_audio.clear()
                elif time.monotonic() - start_time > WAIT_FOR_SPEECH_SECONDS:
                    break
            else:
                chunks.append(audio)
                silent_blocks = 0 if speaking else silent_blocks + 1
                if silent_blocks >= silence_limit:
                    break

    if not speech_started or not chunks:
        return None, None
    recording = np.concatenate(chunks)
    if len(recording) / sample_rate < 0.3:
        return None, None
    return recording, sample_rate


def audio_to_wav(samples: np.ndarray, sample_rate: int) -> io.BytesIO:
    """Convert microphone samples to an in-memory PCM WAV file."""
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
    result = io.BytesIO()
    with wave.open(result, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm.tobytes())
    result.seek(0)
    return result


def transcribe_voice(model: WhisperModel, samples: np.ndarray, sample_rate: int) -> str:
    """Transcribe Hindi, English or Hinglish locally."""
    segments, info = model.transcribe(
        audio_to_wav(samples, sample_rate),
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
        vad_filter=False,
    )
    text = " ".join(part.text.strip() for part in segments).strip()
    if text:
        print(f"Detected language: {info.language}")
        print(f"You: {text}")
    return text


def ask_nova(client: Client, question: str, history: list[dict]) -> str:
    """Stream a local Ollama answer; retain a few conversation turns."""
    messages = [*history, {"role": "user", "content": question}]
    print("\nNova: ", end="", flush=True)
    parts: list[str] = []
    stream = client.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        stream=True,
        keep_alive="30m",
        options={"num_ctx": 2048, "num_predict": 96, "temperature": 0.3},
    )
    for chunk in stream:
        token = chunk.message.content or ""
        print(token, end="", flush=True)
        parts.append(token)
    print("\n")
    answer = "".join(parts).strip()
    if answer:
        history[:] = (messages + [{"role": "assistant", "content": answer}])[-MAX_HISTORY_MESSAGES:]
    return answer


def speak(speaker: pyttsx3.Engine, text: str) -> None:
    """Speak the result with the Windows offline SAPI5 voice."""
    if text:
        clean = re.sub(r"[*_`#]", "", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        speaker.say(clean)
        speaker.runAndWait()


def main() -> int:
    print("Starting Nova Voice...")
    print("Loading local Whisper model (first run may download it)...")
    whisper = WhisperModel(
        WHISPER_MODEL,
        device="cpu",
        compute_type="int8",
        cpu_threads=min(4, os.cpu_count() or 2),
    )
    client = Client(host="http://127.0.0.1:11434", timeout=120)

    speaker = pyttsx3.init("sapi5")
    speaker.setProperty("rate", 185)
    speaker.setProperty("volume", 1.0)
    history: list[dict] = []

    print("\nNova Voice is ready.")
    print("Press Enter to speak, or type q to quit.\n")
    while True:
        try:
            command = input("Press Enter to talk > ").strip().lower()
            if command in ("q", "quit", "exit"):
                break

            samples, sample_rate = record_voice()
            if samples is None or sample_rate is None:
                print("No speech detected.\n")
                continue

            print("Recognizing speech...")
            question = transcribe_voice(whisper, samples, sample_rate)
            if not question:
                print("I couldn't understand that.\n")
                continue

            print("Generating response...")
            answer = ask_nova(client, question, history)
            speak(speaker, answer)

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as exc:
            print(f"\nError: {exc}", file=sys.stderr)
            print("Check Ollama, microphone permissions and audio devices.\n")

    print("Goodbye!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
