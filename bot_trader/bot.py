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
from shared.bybit_client import get_bybit_ticker, get_market_overview

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
    "3. **Анализ живых биржевых данных:**\n"
    "   - Анализ цен, ставок финансирования (Funding Rate) и открытого интереса (Open Interest) для оценки настроений и ликвидаций.\n"
    "4. **Аналитика новостей и постов (Саммари без воды):**\n"
    "   - Выделение ключевых фактов, влияния на волатильность и ценовых триггеров.\n"
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
        "temperature": 0.45,
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

def format_ticker_message(t):
    change_emoji = "🟢" if t["change_pct"] >= 0 else "🔴"
    return (
        f"📊 **Bybit Live [{t['symbol']}]**\n"
        f"• Цена: **${t['price']:,.2f}** ({change_emoji} {t['change_pct']:+.2f}% за 24ч)\n"
        f"• Диапазон 24ч: ${t['low_24h']:,.2f} — ${t['high_24h']:,.2f}\n"
        f"• Объем 24ч: ${t['turnover_24h_m']:,.1f}M\n"
        f"• Открытый интерес (OI): ${t['open_interest_m']:,.1f}M\n"
        f"• Фандинг (Funding Rate): {t['funding_rate_pct']:+.4f}%\n"
    )

def process_updates():
    if not BOT_TOKEN:
        logging.error("TRADER_BOT_TOKEN is empty! Please check .env file.")
        return

    offset = None
    logging.info("Crypto Trader Bot (Voice + Bybit Live Data) started listening...")
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

                # Whitelist
                if ALLOWED_USER_IDS and chat_id not in ALLOWED_USER_IDS:
                    logging.warning(f"Unauthorized trader bot access from ID: {chat_id}")
                    send_message(chat_id, "⛔ Доступ ограничен. Персональный торговый бот.")
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

                logging.info(f"Trader Bot received from {chat_id} (voice={is_voice}): {text[:50]}...")

                if text == "/start":
                    welcome = (
                        "📊 **Crypto & Smart Money Trader AI** (@forexyeah777_bot)\n\n"
                        "Я твой локальный ИИ-аналитик на базе модели **Huihui-Qwen3.6-35B (Claude Opus)** с живыми данными Bybit!\n\n"
                        "⚡ **Возможности:**\n"
                        "🔹 **Живые котировки и фандинг:** реальные данные с биржи Bybit в 1 клик.\n"
                        "🔹 **Голосовые сообщения:** надиктовывай сэтапы голосом — расшифрую через Whisper!\n"
                        "🔹 **Smart Money (SMC):** разбор сэтапов, FVG, Order Blocks, Liquidity Sweeps, BOS/CHoCH.\n"
                        "🔹 **Pine Script v5:** код индикаторов и алертов для TradingView.\n"
                        "🔹 **Саммари новостей:** выжимка сути без «воды».\n\n"
                        "🔥 **Команды:**\n"
                        "• `/p btc` (или `/p eth`, `/p sol`) — живая цена, OI, фандинг + экспресс-анализ ИИ\n"
                        "• `/market` (или `/funding`) — обзор топ-монет и ставок финансирования\n"
                        "• `/smc [сэтап]` — анализ сделки по Smart Money\n"
                        "• `/pine [идея]` — написать код для TradingView\n"
                        "• `/news [текст]` — трейдерская выжимка новости\n"
                        "• `/reset` — очистить память диалога\n\n"
                        "Или просто пиши/надиктовывай вопросы в чат!"
                    )
                    send_message(chat_id, welcome)
                    continue

                if text in ["/reset", "/clear"]:
                    user_histories[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
                    send_message(chat_id, "🧹 Память торгового контекста очищена! Готов к новым сэтапам.")
                    continue

                # Live Market Data Command: /p <symbol>
                if text.startswith("/p") or text.startswith("/price"):
                    parts = text.split()
                    symbol = parts[1] if len(parts) > 1 else "BTC"
                    send_chat_action(chat_id, "typing")
                    ticker = get_bybit_ticker(symbol)
                    if not ticker:
                        send_message(chat_id, f"⚠️ Не удалось получить данные по символу {symbol} с Bybit.")
                        continue

                    header = format_ticker_message(ticker)
                    prompt = (
                        f"Вот актуальные рыночные данные с биржи Bybit для {ticker['symbol']}:\n"
                        f"- Текущая цена: ${ticker['price']}\n"
                        f"- Изменение за 24ч: {ticker['change_pct']:+.2f}%\n"
                        f"- Диапазон за 24ч: ${ticker['low_24h']} - ${ticker['high_24h']}\n"
                        f"- 24h оборот: ${ticker['turnover_24h_m']:.1f} млн\n"
                        f"- Открытый интерес (OI): ${ticker['open_interest_m']:.1f} млн\n"
                        f"- Funding Rate: {ticker['funding_rate_pct']:+.4f}%\n\n"
                        f"Сделай краткий экспертный анализ: есть ли перегрев лонгов/шортов по фандингу, "
                        f"что говорит открытый интерес и где ключевые зоны ликвидности относительно текущего 24h диапазона."
                    )
                    ai_analysis = query_local_model(chat_id, prompt)
                    full_reply = f"{header}\n💡 **Анализ ИИ:**\n{ai_analysis}"
                    send_message(chat_id, full_reply)
                    continue

                # Market Overview Command: /market or /funding
                if text in ["/market", "/funding", "/fr"]:
                    send_chat_action(chat_id, "typing")
                    overview = get_market_overview()
                    if not overview:
                        send_message(chat_id, "⚠️ Не удалось загрузить данные с Bybit.")
                        continue
                    
                    lines = ["📊 **Обзор рынка Bybit Linear (Фандинг и Объемы):**\n"]
                    for t in overview:
                        lines.append(f"• **{t['symbol']}**: ${t['price']:,.2f} ({t['change_pct']:+.2f}%) | Funding: {t['funding_rate_pct']:+.4f}% | OI: ${t['open_interest_m']:,.0f}M")
                    
                    market_text = "\n".join(lines)
                    prompt = (
                        f"{market_text}\n\n"
                        f"Оцени общую рыночную картину: кто из лидеров перегрет по фандингу, куда направлена ликвидность?"
                    )
                    ai_analysis = query_local_model(chat_id, prompt)
                    send_message(chat_id, f"{market_text}\n\n💡 **Анализ настроений:**\n{ai_analysis}")
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
                if is_voice:
                    reply = f"🎙️ *Распознано:* «{text}»\n\n{reply}"
                send_message(chat_id, reply)

        except Exception as e:
            logging.error(f"Error in trader bot update loop: {e}")
            time.sleep(2)

if __name__ == "__main__":
    process_updates()
