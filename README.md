# 🚀 Local AI Suite (Qwen 35B + Claude Opus Distillation)

Комплекс персональных Telegram-ботов, работающих на локальной языковой модели **`Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated`** через **LM Studio Local Server**.

---

## 🔒 Ключевые особенности
- **100% приватность:** все вычисления выполняются на вашем локальном ПК, данные не уходят во внешние облака.
- **Встроенный Whitelist:** боты отвечают только владельцу по его Telegram ID (защита от несанкционированного доступа).
- **Снятые ограничения (Abliterated):** модель отвечает прямо, без корпоративных отказов и морализаторства.
- **Два специализированных агента:**
  1. `bot_assistant` — персональный ассистент для общих задач, текстов, кода и логики.
  2. `bot_trader` — профильный ассистент по **Smart Money (SMC)**, **Price Action**, крипторынку, анализу FVG/Order Blocks и генерации индикаторов на **Pine Script v5**.

---

## 📁 Структура проекта
```text
local-ai-suite/
├── .gitignore               # Исключение .env и временных файлов из репозитория
├── .env                     # Ваши персональные токены (не коммитится в Git!)
├── config.example.env       # Шаблон конфигурационного файла
├── requirements.txt         # Зависимости Python
├── bot_assistant/           # Модуль персонального ассистента
│   ├── bot.py
│   └── run.bat              # Запуск в 1 клик
├── bot_trader/              # Модуль трейдинг-ассистента (Smart Money)
│   ├── bot.py
│   └── run.bat              # Запуск в 1 клик
└── scripts/                 # Вспомогательные скрипты
    └── test_model.py        # Быстрый тест доступности модели через терминал
```

---

## ⚙️ Установка и запуск

### 1. Подготовка LM Studio
1. Скачайте и загрузите модель `Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated`.
2. Перейдите во вкладку **Developer -> Local Server** (или Model Server).
3. Включите тумблер **Status: Running** (порт по умолчанию: `http://127.0.0.1:1234`).

### 2. Настройка окружения
Скопируйте `config.example.env` в `.env` и укажите ваши токены Telegram:
```ini
LM_STUDIO_URL=http://127.0.0.1:1234/v1/chat/completions
MODEL_NAME=huihui-qwen3.6-35b-a3b-claude-4.7-opus-abliterated
ALLOWED_USER_IDS=7368784594
ASSISTANT_BOT_TOKEN=ВАШ_ТОКЕН_БОТА_1
TRADER_BOT_TOKEN=ВАШ_ТОКЕН_БОТА_2
```

### 3. Запуск ботов
- Для запуска персонального ассистента дважды кликните: `bot_assistant/run.bat`
- Для запуска трейдинг-бота дважды кликните: `bot_trader/run.bat`
