# Nova Voice — Local Windows Voice Assistant (Ollama 0.5B)

A lightweight, CPU-only, **push-to-talk** voice assistant for an 8 GB Windows laptop.
It uses **Qwen2.5 0.5B** via Ollama, **Faster-Whisper Tiny** for local English/Hindi/Hinglish recognition, and **Windows SAPI5** text-to-speech.

## Requirements

- Windows 10/11, ~8 GB RAM, microphone and speakers
- [Ollama for Windows](https://ollama.com/download/windows) installed and **running**
- Python **3.11 (64-bit)** installed with the `py` launcher
- Internet for first-time installation/model downloads; once installed, model inference runs locally

## Quick setup

1. Extract this ZIP (for example, to `C:\Users\YOUR_NAME\NovaVoice`).
2. Open PowerShell in the extracted **NovaVoice** directory.
3. Run:

   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1
   ```

   The script creates `.venv`, installs packages, downloads `qwen2.5:0.5b`, creates `nova-voice`, and caches the Whisper Tiny model.
4. Start by double-clicking **run_windows.bat**, or run:

   ```powershell
   .\.venv\Scripts\python.exe .\voice_assistant.py
   ```

5. Press **Enter**, speak, then pause. Nova transcribes, responds, and speaks. Type **q** and Enter to quit.

## Manual setup (alternative)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen2.5:0.5b
ollama create nova-voice -f Modelfile
.\.venv\Scripts\python.exe .\voice_assistant.py
```

## Troubleshooting

- **`ollama` not found:** Install/start Ollama and reopen PowerShell. See https://ollama.com/download/windows.
- **Connection refused on port 11434:** Start Ollama from Windows Start menu, or run `ollama serve` in a separate terminal if no server is already running.
- **`py -3.11` not found:** Install Python 3.11 (64-bit). Do not rely on Python 3.13 for this project.
- **No microphone input:** Windows Settings > Privacy & security > Microphone > enable desktop app access. To list devices:

  ```powershell
  .\.venv\Scripts\python.exe -c "import sounddevice as sd; print(sd.query_devices())"
  ```

- **Background noise triggers recording:** Increase `MIC_THRESHOLD` in `voice_assistant.py` to `0.025`. If quiet speech is missed, lower it to `0.005`.
- **Hindi accuracy:** Change `WHISPER_MODEL = "tiny"` to `"base"` (slower, additional first-use download).
- **Hindi voice sounds unnatural:** Windows SAPI5 varies by installed voices; Romanized Hindi may sound unnatural with an English voice. A Hindi-capable offline TTS engine is a future upgrade.
- **Response is too slow:** Leave `WHISPER_MODEL = "tiny"`, keep `num_ctx = 2048`, and close memory-intensive applications. First inference may be slower while Ollama loads the model.
- **Python imports fail:** Ensure you run `.venv\Scripts\python.exe` and rerun `setup_windows.ps1`.

## Files

- `Modelfile`: custom Ollama model instructions and parameters
- `voice_assistant.py`: microphone -> speech recognition -> Ollama -> spoken reply
- `requirements.txt`: Python packages
- `setup_windows.ps1`: automatic installation, model creation, Whisper download
- `run_windows.bat`: quick launcher

## Notes

- This project customizes an existing pretrained model; **it does not train a new LLM**.
- Transcribed text is processed locally by the Ollama server on `127.0.0.1:11434`.
- This is **not** a wake-word or full-duplex assistant. Press Enter to speak; the assistant speaks *after* the answer is generated.
- First-use Whisper model caching accesses Hugging Face to download model files.
- Without a suitable Hindi SAPI5 voice, English/Hinglish spoken output may be easier to understand than Hindi.
