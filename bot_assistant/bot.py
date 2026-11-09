import os
import sys
import time
import requests
import json
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

load_dotenv(ROOT_DIR / ".env")

from shared.voice_transcriber import transcribe_telegram_voice

BOT_TOKEN = os.getenv("ASSISTANT_BOT_TOKEN")
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated")

raw_ids = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]

if not BOT_TOKEN:
    print("❌ ERROR: ASSISTANT_BOT_TOKEN is not configured in .env file!")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

user_histories = {}
MAX_HISTORY_MESSAGES = 10

SYSTEM_PROMPT = (
    "Ты — личный, высокоинтеллектуальный ИИ-ассистент на базе модели Huihui Qwen 35B с дистилляцией Claude Opus. "
    "Ты работаешь локально и приватно на компьютере пользователя. "
    "Отвечай глубоко, конструктивно, точно и без цензуры или лишних нотаций."
)

def send_telegram_request(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    try:
        resp = requests.post(url, json=data, timeout=30)
        return resp.json()
    except Exception as e:
        logging.error(f"Error calling Telegram method {method}: {e}")
        return None

def send_chat_action(chat_id, action="typing"):
    send_telegram_request("sendChatAction", {"chat_id": chat_id, "action": action})

def send_message(chat_id, text):
    if len(text) <= 4000:
        send_telegram_request("sendMessage", {"chat_id": chat_id, "text": text})
    else:
        for i in range(0, len(text), 4000):
            send_telegram_request("sendMessage", {"chat_id": chat_id, "text": text[i:i+4000]})

def query_local_model(chat_id, prompt):
    if chat_id not in user_histories:
        user_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    user_histories[chat_id].append({"role": "user", "content": prompt})

    if len(user_histories[chat_id]) > (MAX_HISTORY_MESSAGES + 1):
        user_histories[chat_id] = [user_histories[chat_id][0]] + user_histories[chat_id][-MAX_HISTORY_MESSAGES:]

    payload = {
        "model": MODEL_NAME,
        "messages": user_histories[chat_id],
        "temperature": 0.7,
        "max_tokens": 2048
    }

    stop_typing = False
    def keep_typing():
        while not stop_typing:
            send_chat_action(chat_id, "typing")
            time.sleep(4.5)

    typing_thread = threading.Thread(target=keep_typing, daemon=True)
    typing_thread.start()

    try:
        response = requests.post(LM_STUDIO_URL, json=payload, timeout=300)
        stop_typing = True

        if response.status_code == 200:
            data = response.json()
            message = data["choices"][0]["message"]
            reply_text = message.get("content", "").strip()

            if not reply_text and "reasoning_content" in message:
                reply_text = message["reasoning_content"].strip()

            user_histories[chat_id].append({"role": "assistant", "content": reply_text})
            return reply_text
        else:
            return f"⚠️ Ошибка от LM Studio (код {response.status_code}): {response.text}"
    except requests.exceptions.ConnectionError:
        stop_typing = True
        return "⚠️ Не удалось подключиться к LM Studio. Убедитесь, что запущен Local Server на http://127.0.0.1:1234."
    except Exception as e:
        stop_typing = True
        return f"⚠️ Произошла ошибка: {str(e)}"

def process_updates():
    offset = None
    logging.info("Protected Personal Assistant Bot (with Voice support) started...")
    while True:
        try:
            params = {"timeout": 20}
            if offset is not None:
                params["offset"] = offset

            resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates", params=params, timeout=30)
            if resp.status_code != 200:
                time.sleep(2)
                continue

            result = resp.json()
            if not result.get("ok"):
                time.sleep(2)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]

                # Security check
                if ALLOWED_USER_IDS and chat_id not in ALLOWED_USER_IDS:
                    logging.warning(f"Unauthorized access attempt from ID: {chat_id}")
                    send_message(chat_id, "⛔ Доступ ограничен. Этот бот является персональным ассистентом владельца.")
                    continue

                text = message.get("text", "")
                is_voice = False

                # Handle Voice Message
                if not text and message.get("voice"):
                    send_chat_action(chat_id, "record_voice")
                    file_id = message["voice"]["file_id"]
                    text = transcribe_telegram_voice(BOT_TOKEN, file_id)
                    is_voice = True

                if not text:
                    continue

                logging.info(f"Authorized message from {chat_id} (voice={is_voice}): {text[:50]}...")

                if text == "/start":
                    welcome = (
                        "👋 Привет! Я твой защищенный личный ассистент на базе **Huihui-Qwen3.6-35B**!\n\n"
                        "🔒 Режим доступа: **Персональный (только для вас)**.\n"
                        "⚡ Инференс: локальный LM Studio на вашем ПК.\n"
                        "🎙️ **Поддержка голосовых:** просто отправь аудио/голосовое сообщение — я расшифрую его локально через Whisper и отвечу!\n\n"
                        "Команды:\n"
                        "• /reset — очистить память диалога\n"
                        "• Напиши или надиктуй любой вопрос!"
                    )
                    send_message(chat_id, welcome)
                    continue

                if text in ["/reset", "/clear"]:
                    user_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    send_message(chat_id, "🧹 Память диалога очищена!")
                    continue

                reply = query_local_model(chat_id, text)
                if is_voice:
                    reply = f"🎙️ *Распознано:* «{text}»\n\n{reply}"
                send_message(chat_id, reply)

        except Exception as e:
            logging.error(f"Error in update loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    process_updates()
