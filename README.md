# 🚀 Local AI Suite (Qwen 35B + Claude Opus Distillation)

Комплекс персональных Telegram-ботов, работающих на локальной языковой модели **`Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated`** через **LM Studio Local Server**.

---

## 🌟 Ключевые возможности

1. **🎙️ Голосовые сообщения (Voice-to-Text с Faster-Whisper):**
   - Отправляйте голосовые сообщения прямо с телефона — бот мгновенно расшифровывает речь через локальный Whisper и отвечает текстом.
2. **⚡ Автозапуск вместе с Windows:**
   - Скрипт в автозагрузке запускает обоих ботов бесшумно в фоновом режиме при старте системы.
3. **📊 Прямая интеграция с биржей Bybit (Live Data):**
   - Команды `/p btc`, `/p eth`, `/p sol` для получения реальных котировок, 24h объемов, открытого интереса (OI) и ставки финансирования (Funding Rate) с экспресс-анализом ИИ.
   - Команда `/market` для обзора рынка и перегрева фандинга.
4. **📈 Smart Money Concepts PRO Indicator (TradingView Pine Script v5):**
   - Готовый профессиональный индикатор в папке `indicators/smc_pro.pine` (автоматическая разметка FVG, Order Blocks, Asian Range Liquidity и алерты).
5. **🔒 Защита Whitelist:**
   - Боты жестко привязаны к вашему Telegram ID и игнорируют посторонних.

---

## 📁 Структура проекта
```text
local-ai-suite/
├── .gitignore               # Исключение .env и временных файлов
├── .env                     # Ваши персональные токены (не коммитится в Git!)
├── config.example.env       # Шаблон конфигурации
├── requirements.txt         # Зависимости Python
├── README.md                # Полная документация
├── start_all_silent.vbs     # Бесшумный запуск обоих ботов в фоне
├── start_all_visible.bat    # Запуск с видимыми консолями
├── push_to_github.bat       # Синхронизация с GitHub в 1 клик
├── bot_assistant/           # Бот 1: Личный ассистент + Voice Whisper
│   ├── bot.py
│   └── run.bat
├── bot_trader/              # Бот 2: Трейдинг Smart Money + Bybit Live Data + Voice
│   ├── bot.py
│   └── run.bat
├── shared/                  # Общие модули
│   ├── bybit_client.py      # Клиент Bybit Live API
│   └── voice_transcriber.py # Локальное распознавание речи Whisper
└── indicators/              # Индикаторы для TradingView
    └── smc_pro.pine         # Индикатор Smart Money Concepts PRO (Pine Script v5)
```

---

## ⚡ Быстрые команды трейдинг-бота (@forexyeah777_bot)

- `/p btc` (или `/p sol`, `/p eth`) — живая цена, открытый интерес, фандинг и экспресс-анализ ИИ
- `/market` — обзор фандинга и лидеров рынка
- `/smc [описание сэтапа]` — мгновенный разбор сделки по концепциям Smart Money
- `/pine [идея]` — генерация скрипта для TradingView
- `/news [текст]` — аналитическая выжимка без «воды»
- **Голосовое сообщение** — надиктуйте любой сэтап голосом с телефона!

---

## 🛠️ Как установить индикатор в TradingView:
1. Откройте файл `indicators/smc_pro.pine`.
2. Скопируйте весь код.
3. В TradingView откройте снизу вкладку **Pine Editor** (Редактор Pine).
4. Вставьте код и нажмите **Добавить на график (Add to chart)**.
