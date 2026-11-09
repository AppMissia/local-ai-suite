import os
import tempfile
import requests
import logging

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        logging.info("Initializing Faster-Whisper model ('base' on CPU int8)...")
        from faster_whisper import WhisperModel
        # Using base model with 8 CPU threads for fast transcription
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8", cpu_threads=8)
        logging.info("Faster-Whisper model ready!")
    return _whisper_model

def transcribe_telegram_voice(bot_token: str, file_id: str) -> str:
    """Downloads voice file from Telegram and transcribes it to text."""
    try:
        # 1. Get file path from Telegram
        url_info = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        resp = requests.get(url_info, timeout=20).json()
        if not resp.get("ok"):
            return ""
        
        file_path = resp["result"]["file_path"]
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        
        # 2. Download into temporary audio file
        ext = os.path.splitext(file_path)[1] or ".oga"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_path = tmp.name
            audio_data = requests.get(download_url, timeout=30).content
            tmp.write(audio_data)

        # 3. Transcribe via Whisper
        try:
            model = get_whisper_model()
            segments, info = model.transcribe(tmp_path, beam_size=5)
            transcribed_text = " ".join([segment.text for segment in segments]).strip()
            logging.info(f"Voice transcribed ({info.language}, prob={info.language_probability:.2f}): {transcribed_text}")
            return transcribed_text
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    except Exception as e:
        logging.error(f"Error transcribing voice message: {e}")
        return ""
