# Content Intelligence Bot — MVP

Telegram-бот для маркетинговой команды: анализирует публичный Instagram-контент блогера за последние 24 часа и возвращает структурированную сводку по блокам A / B / C.

---

## Стек

| Слой | Технология |
|---|---|
| Telegram | aiogram 3.x |
| Job queue | ARQ + Redis |
| DB | PostgreSQL 16 + SQLAlchemy async + Alembic |
| Cache | Redis |
| Instagram | instaloader (публичные профили) |
| STT | faster-whisper (модель `small`, CPU) |
| OCR | easyocr (CPU) |
| LLM | OpenAI API (`gpt-4o`, OpenAI-compatible) |
| Media | локальный Docker volume `/data/media` |

---

## Быстрый старт (docker-compose)

### 1. Скопируй `.env`

```bash
cp .env.example .env
```

Открой `.env` и заполни обязательные поля:

```env
TELEGRAM_BOT_TOKEN=...   # @BotFather
OPENAI_API_KEY=...       # platform.openai.com/api-keys  (или другой провайдер)
OPENAI_MODEL=gpt-4o
COLLECTOR_PROVIDER=mock  # "mock" для теста без реального Instagram
LLM_MOCK=false           # true — пайплайн без реального LLM (для разработки)
```

### 2. Подними сервисы

```bash
docker-compose up --build
```

Первый запуск (~5–10 мин): Docker скачает образ Python, установит зависимости (easyocr + torch CPU — ~2 GB).

При старте автоматически:
- поднимается PostgreSQL и Redis
- выполняются миграции Alembic (`migrate` сервис)
- стартуют `bot` и `worker`

### 3. Проверь бот

Открой своего бота в Telegram:

```
/start
/analyze @someuser
/last
```

При `COLLECTOR_PROVIDER=mock` бот использует встроенные тестовые данные — ответ придёт за ~30–60 сек.

---

## Команды бота

| Команда | Описание |
|---|---|
| `/start` | Приветствие |
| `/help` | Справка по командам |
| `/analyze @handle` | Запустить анализ (ручной режим) |
| `/last` | Последняя сводка из кэша |

После `/analyze` бот присылает:
1. Краткую human-readable сводку (блоки A, B, C)
2. Статус пайплайна
3. Кнопку «Получить JSON» → документ с полным JSON результата

---

## Реальный Instagram (без mock)

```env
COLLECTOR_PROVIDER=instagram
```

instaloader работает с публичными профилями без авторизации. При rate-limit Instagram можно добавить файл сессии:

```bash
# Войди в instaloader один раз:
instaloader --login YOUR_INSTAGRAM_LOGIN
# Скопируй файл сессии:
INSTAGRAM_SESSION_FILE=/data/instagram_session
```

---

## Локальный запуск (без Docker)

### Требования
- Python 3.11+
- PostgreSQL 16
- Redis 7
- ffmpeg (`apt install ffmpeg` / `brew install ffmpeg`)

```bash
# Создай виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Установи зависимости
pip install -r requirements.txt

# Скопируй и заполни .env
cp .env.example .env
# Укажи локальные DSN:
# POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/botdb
# REDIS_URL=redis://localhost:6379/0

# Примени миграции
alembic upgrade head

# В терминале 1 — бот:
python -m app.bot.main

# В терминале 2 — воркер:
python -m arq app.workers.main.WorkerSettings
```

---

## Тесты

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

Тесты не требуют PostgreSQL, Redis или OpenAI API — используют только mock-данные.

---

## Структура проекта

```
app/
├── bot/
│   ├── main.py              # aiogram polling
│   ├── formatters.py        # human-readable сводки из AnalysisResult
│   └── handlers/
│       ├── commands.py      # /start /help /analyze /last
│       └── callbacks.py     # inline кнопка JSON
├── collectors/
│   ├── base.py              # ABC ContentCollector
│   ├── instagram.py         # instaloader adapter
│   ├── mock.py              # фикстурные данные
│   └── factory.py           # выбор провайдера через ENV
├── processors/
│   ├── downloader.py        # httpx download с retry
│   ├── audio_extractor.py   # ffmpeg video→wav
│   └── keyframe_extractor.py # ffmpeg video→jpg
├── services/
│   ├── stt.py               # faster-whisper
│   ├── ocr.py               # easyocr
│   └── llm.py               # OpenAI function-calling → strict JSON
├── workers/
│   ├── main.py              # ARQ WorkerSettings
│   └── analyze_job.py       # run_analysis() пайплайн
├── schemas/
│   ├── analysis.py          # AnalysisResult + все sub-схемы
│   ├── job.py               # JobCreate, JobRead
│   └── collector.py         # ContentItem
├── models/                  # SQLAlchemy ORM
├── repos/                   # DB CRUD
├── prompts/
│   └── analysis_v1.txt      # LLM системный промпт
├── config/
│   └── providers.py         # AI config constants
└── core/
    ├── config.py            # Pydantic Settings
    ├── database.py          # async SQLAlchemy engine
    ├── cache.py             # Redis wrapper
    └── logging.py           # structlog
```

---

## Graceful degradation

| Сценарий | Поведение |
|---|---|
| STT fail + OCR ok | Продолжаем, `pipeline_status.stt = "failed"` |
| OCR fail + STT ok | Продолжаем, `pipeline_status.ocr = "failed"` |
| Оба fail | LLM получает только caption-текст |
| Collector partial | Берём что есть, `collector = "partial"` |
| LLM fail | Возвращаем пустой результат с `llm = "failed"` |
| Контент 0 единиц | Предупреждение в `warnings` |

Все partial failures фиксируются в `pipeline_status` и `warnings` JSON.

---

## Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Токен бота | **обязательно** |
| `OPENAI_API_KEY` | Ключ OpenAI | **обязательно** (если `LLM_MOCK=false`) |
| `OPENAI_MODEL` | Модель OpenAI | `gpt-4o` |
| `OPENAI_BASE_URL` | Кастомный эндпоинт (Azure, vLLM…) | `None` |
| `LLM_MOCK` | `true` — мок-режим без реального LLM | `false` |
| `POSTGRES_DSN` | DSN PostgreSQL | см. docker-compose |
| `REDIS_URL` | URL Redis | `redis://redis:6379/0` |
| `COLLECTOR_PROVIDER` | `mock` или `instagram` | `mock` |
| `INSTAGRAM_SESSION_FILE` | Путь к файлу сессии instaloader | `None` |
| `WHISPER_MODEL` | Модель faster-whisper | `small` |
| `WHISPER_DEVICE` | `cpu` или `cuda` | `cpu` |
| `MEDIA_ROOT` | Директория для медиа | `/data/media` |
| `MEDIA_TTL_DAYS` | TTL сырых медиафайлов (дни) | `7` |
| `CACHE_TTL_SECONDS` | TTL Redis кэша | `3600` |
| `ANALYSIS_WINDOW_HOURS` | Окно анализа (часы) | `24` |
| `WORKER_CONCURRENCY` | Параллельных ARQ jobs | `4` |

---

## Следующие шаги (этап 2+)

- [ ] Watchlist + планировщик (ARQ cron)
- [ ] Вторая платформа (adapter уже готов — добавить `TikTokCollector`)
- [ ] GEO-локализация (поле в схеме уже предусмотрено)
- [ ] Creative angles блок (новый раздел в LLM prompt)
- [ ] GPU-ускорение Whisper (`WHISPER_DEVICE=cuda`)
- [ ] S3-хранилище для медиа (заменить `local_path` на S3 URL в downloader)
- [ ] Admin UI (Streamlit / FastAPI dashboard)
- [ ] Ротация Instagram cookies для снижения rate-limit
