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
    "Ты — элитный трейдер-аналитик, квант и эксперт по концепциям Smart Money (SMC), Price Action и криптовалютному рынку.\n"
    "Твои специализации:\n"
    "1. **Smart Money Concepts (SMC):**\n"
    "   - Идентификация Order Block (OB), Fair Value Gap (FVG / Имбаланс), Liquidity Sweeps (снятие ликвидности / охота за стопами), Inducement (IDM).\n"
    "   - Определение структуры: BOS (Break of Structure), CHoCH (Change of Character), Premium/Discount зоны по Fibonacci (0.618-0.786 OTE).\n"
    "2. **Кодинг и автоматизация (Pine Script v5):**\n"
    "   - Написание рабочих, оптимизированных скриптов и индикаторов для TradingView (версия strictly //@version=5).\n"
    "   - Добавление алертов через alertcondition() и визуальных меток на графике.\n"
    "   - Написание Python-скриптов для Bybit/Binance API и ccxt (парсеры, трекинг ликвидаций, сканеры объемов).\n"
    "3. **Аналитика новостей и постов (Саммари без воды):**\n"
    "   - При анализе новостей или пересланных сообщений выдавай структуру:\n"
    "     • Ключевой факт (в 1-2 предложениях)\n"
    "     • Влияние на рынок (бычье / медвежье / всплеск волатильности)\n"
    "     • Торговые выводы и зоны внимания\n"
    "4. **Риск-менеджмент:**\n"
    "   - Всегда проверяй Risk/Reward (минимум 1:2.5, идеал 1:3+), четкий уровень инвалидации сэтапа (Stop Loss).\n"
    "Отвечай уверенно, профессионально, структурированно, используй форматирование списков и блоков кода."
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
        "temperature": 0.45,  # High precision for financial analysis and code
        "max_tokens": 2500
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
    if not BOT_TOKEN:
        logging.error("TRADER_BOT_TOKEN is empty! Please check .env file.")
        return

    offset = None
    logging.info("Crypto & Smart Money Trader Bot started listening...")
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

                # Whitelist authorization
                if ALLOWED_USER_IDS and chat_id not in ALLOWED_USER_IDS:
                    logging.warning(f"Unauthorized trader bot access from ID: {chat_id}")
                    send_message(chat_id, "⛔ Доступ ограничен. Этот бот настроен только для персональной торговли владельца.")
                    continue

                text = message.get("text", "")
                if not text:
                    continue

                logging.info(f"Trader Bot received from {chat_id}: {text[:50]}...")

                if text == "/start":
                    welcome = (
                        "📊 **Crypto & Smart Money Trader AI** (@forexyeah777_bot)\n\n"
                        "Я твой локальный ИИ-аналитик на базе модели **Huihui-Qwen3.6-35B (Claude Opus)**.\n\n"
                        "⚡ **Что я умею:**\n"
                        "🔹 **Smart Money (SMC):** разбор сэтапов, FVG, Order Blocks, Liquidity Sweeps, BOS/CHoCH, Premium/Discount.\n"
                        "🔹 **Pine Script v5:** генерация индикаторов и алертов для TradingView под любую стратегию.\n"
                        "🔹 **Python скрипты:** код для сбора данных с Bybit/Binance, сканеры объемов и стаканов.\n"
                        "🔹 **Саммари постов:** просто перешли сюда новость или пост из каналов — выдам сухую суть и влияние на рынок.\n"
                        "🔹 **Риск-менеджмент:** расчет размера позиции и R:R.\n\n"
                        "Команды:\n"
                        "• `/smc [описание сэтапа]` — мгновенный разбор сделки\n"
                        "• `/pine [идея индикатора]` — написать код для TradingView\n"
                        "• `/news [текст]` — быстрая выжимка новости без спама\n"
                        "• `/reset` — очистить память диалога\n\n"
                        "Либо просто напиши любой вопрос или опиши сделку!"
                    )
                    send_message(chat_id, welcome)
                    continue

                if text in ["/reset", "/clear"]:
                    user_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    send_message(chat_id, "🧹 Память торгового контекста очищена! Готов к новым сэтапам.")
                    continue

                # Process command prefixes or normal queries
                prompt = text
                if text.startswith("/smc"):
                    prompt = "Проведи детальный Smart Money разбор следующего сэтапа/ситуации: " + text[4:].strip()
                elif text.startswith("/pine"):
                    prompt = "Напиши чистый, рабочий код индикатора/стратегии на TradingView Pine Script (версия strict //@version=5) со всеми алертами и пояснениями по следующему ТЗ: " + text[5:].strip()
                elif text.startswith("/news"):
                    prompt = "Сделай профессиональную трейдерскую выжимку без воды следующего текста/новости: " + text[5:].strip()

                reply = query_local_model(chat_id, prompt)
                send_message(chat_id, reply)

        except Exception as e:
            logging.error(f"Error in trader bot update loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    process_updates()
