# 2GIS Business Parser Bot

Telegram-бот для поиска бизнесов без сайта через 2GIS API с генерацией холодных сообщений через OpenRouter.

## Команды

- `/start` — приветствие и инструкция
- `/parse <категория> <город> <страниц>` — запуск парсинга

**Пример:** `/parse автосервис Краснодар 3`

## Установка

```bash
pip install -r requirements.txt
cp .env.example .env
# заполнить .env своими ключами
python bot.py
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `TELEGRAM_TOKEN` | Токен бота от @BotFather |
| `GIS_KEY` | API-ключ 2GIS |
| `OPENROUTER_KEY` | API-ключ OpenRouter |
| `MY_SITE` | Ваш сайт-портфолио |
| `MY_TG` | Ваш Telegram для контакта |

## Деплой на Render

1. Создать Web Service
2. Указать Start Command: `python bot.py`
3. Добавить переменные окружения из `.env`
