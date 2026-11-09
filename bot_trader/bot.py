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
load_dotenv(ROOT_DIR / ".env")

BOT_TOKEN = os.getenv("TRADER_BOT_TOKEN")
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated")

raw_ids = os.getenv("ALLOWED_USER_IDS", "")
ALLOWED_USER_IDS = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

user_histories = {}
MAX_HISTORY_MESSAGES = 10

SYSTEM_PROMPT = (
    "Ты — профессиональный трейдер-аналитик и эксперт по концепциям Smart Money (SMC), Price Action и криптовалютному рынку. "
    "Твои специализации:\n"
    "1. Анализ рыночной структуры: Order Block (OB), Fair Value Gap (FVG), Liquidity Sweeps, BOS, CHoCH, Premium/Discount зоны.\n"
    "2. Риск-менеджмент: расчет Risk/Reward (R:R), уровней инвалидации (Stop Loss) и фиксации (Take Profit), контроль плеча.\n"
    "3. Разработка: написание индикаторов и стратегий на Pine Script (TradingView v5), скриптов на Python (ccxt, pandas_ta, Bybit/Binance API).\n"
    "4. Саммари новостей: выжимка сути без воды из новостных лент и постов с упором на влияние на волатильность.\n"
    "Отвечай четко, структурированно, профессионально и без шаблонных отговорок."
)

def send_telegram_request(method, data=None):
    if not BOT_TOKEN:
        return None
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
        "temperature": 0.5, # Slightly lower temperature for trading/math precision
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
        return "⚠️ Не удалось подключиться к LM Studio. Убедитесь, что Local Server активен."
    except Exception as e:
        stop_typing = True
        return f"⚠️ Произошла ошибка: {str(e)}"

def process_updates():
    if not BOT_TOKEN:
        logging.error("TRADER_BOT_TOKEN is empty! Please add TRADER_BOT_TOKEN into .env file.")
        return

    offset = None
    logging.info("Protected Smart Money & Crypto Trader Bot started...")
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

                if ALLOWED_USER_IDS and chat_id not in ALLOWED_USER_IDS:
                    logging.warning(f"Unauthorized trader bot access from ID: {chat_id}")
                    send_message(chat_id, "⛔ Доступ ограничен.")
                    continue

                text = message.get("text", "")
                if not text:
                    continue

                logging.info(f"Trader Bot received from {chat_id}: {text[:50]}...")

                if text == "/start":
                    welcome = (
                        "📈 **Smart Money & Crypto Trader AI**\n\n"
                        "Я твой локальный ИИ-ассистент по трейдингу на базе **Qwen 35B (Claude Opus)**.\n\n"
                        "🎯 **Чем я могу помочь:**\n"
                        "• Анализ сэтапов: Order Blocks, FVG, пулы ликвидности, BOS/CHoCH\n"
                        "• Расчет риск-менеджмента (R:R, объем позиции, стоп/тейк)\n"
                        "• Написание индикаторов на **Pine Script v5** для TradingView\n"
                        "• Скрипты на Python (ccxt, Bybit/Binance API)\n"
                        "• Разбор новостей и сигналов без «воды»\n\n"
                        "Команды:\n"
                        "• /reset — очистить память диалога\n"
                        "Отправь сэтап, вопрос или код стратегии!"
                    )
                    send_message(chat_id, welcome)
                    continue

                if text in ["/reset", "/clear"]:
                    user_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    send_message(chat_id, "🧹 Память торгового диалога очищена!")
                    continue

                reply = query_local_model(chat_id, text)
                send_message(chat_id, reply)

        except Exception as e:
            logging.error(f"Error in update loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    process_updates()
