# 💎 StarsPay Bot

**Универсальная платформа оплаты через Telegram Stars** — принимайте платежи для любых GitHub проектов.

## 🌟 Возможности

- 💳 **Оплата Telegram Stars** — встроенная платёжная система Telegram
- 📦 **Мульти-проекты** — один бот для оплаты нескольких проектов
- 🔑 **Лицензионные ключи** — автоматическая генерация и проверка
- 🌐 **Mini App** — красивый веб-интерфейс на GitHub Pages
- 🔗 **REST API** — проверка лицензий из ваших проектов
- 👥 **Реферальная программа** — бонусы за приглашения
- 👑 **Админ-панель** — статистика и управление

## 🚀 Быстрый старт

### Развертывание на Render.com (бесплатно)

1. Нажмите кнопку ниже:
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

2. Установите переменные окружения:
   - `BOT_TOKEN` — токен бота от @BotFather
   - `ADMIN_IDS` — ваш Telegram ID
   - `API_KEYS` — ключи для REST API (через запятую)

3. Готово! Бот запущен 24/7.

### Локально с Docker

```bash
# Клонируйте репозиторий
git clone https://github.com/sochiautoparts/stars-pay-bot.git
cd stars-pay-bot

# Создайте .env файл
echo "BOT_TOKEN=ваш_токен" > .env
echo "ADMIN_IDS=ваш_id" >> .env
echo "API_KEYS=ваш_api_key" >> .env

# Запустите
docker compose up -d
```

### Локально без Docker

```bash
pip install -r requirements.txt
export BOT_TOKEN="ваш_токен"
export ADMIN_IDS="ваш_id"
python -m bot.main
```

## 🌐 Mini App

Mini App доступен по адресу: **https://sochiautoparts.github.io/stars-pay-bot/**

Для подключения к боту:
1. Откройте @BotFather
2. Выберите `/newapp` или отредактируйте меню бота
3. Укажите URL: `https://sochiautoparts.github.io/stars-pay-bot/`

## 🔗 REST API

### Проверка лицензии

```bash
curl -X POST https://ваш-бот.render.com/api/v1/verify \
  -H "X-API-Key: ваш_api_key" \
  -H "Content-Type: application/json" \
  -d '{"key": "SP-GMA-A1B2-C3D4"}'
```

Ответ:
```json
{
  "valid": true,
  "project": "gitmoji-ai",
  "plan": "month",
  "expires_at": 1735689600,
  "is_lifetime": false
}
```

### Проверка пользователя

```bash
curl -X POST https://ваш-бот.render.com/api/v1/check \
  -H "X-API-Key: ваш_api_key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 12345, "project": "gitmoji-ai"}'
```

### Список проектов

```bash
curl https://ваш-бот.render.com/api/v1/projects
```

## 🔧 Интеграция с проектами

### Python

```python
import requests

STARSPAY_API = "https://ваш-бот.render.com"
STARSPAY_KEY = "ваш_api_key"

def check_license(key: str) -> bool:
    resp = requests.post(
        f"{STARSPAY_API}/api/v1/verify",
        headers={"X-API-Key": STARSPAY_KEY},
        json={"key": key}
    )
    return resp.json().get("valid", False)
```

### GitHub Action

```yaml
- name: Verify License
  env:
    LICENSE_KEY: ${{ secrets.LICENSE_KEY }}
  run: |
    VALID=$(curl -s -X POST https://ваш-бот.render.com/api/v1/verify \
      -H "X-API-Key: ${{ secrets.STARSPAY_API_KEY }}" \
      -H "Content-Type: application/json" \
      -d "{\"key\": \"$LICENSE_KEY\"}" | jq -r '.valid')
    [ "$VALID" = "true" ] || exit 1
```

## 👑 Админ-команды

| Команда | Описание |
|---------|----------|
| `/admin` | Статистика бота |
| `/addproject id\|Название\|Описание\|PREFIX` | Добавить проект |
| `/addplan project\|plan\|Название\|цена\|дни` | Добавить тариф |
| `/genkey project\|plan\|user_id` | Создать ключ вручную |
| `/addapikey project\|описание` | Создать API ключ |

## 📦 Структура проекта

```
stars-pay-bot/
├── bot/              # Telegram Bot (aiogram 3.x)
│   ├── main.py       # Точка входа
│   ├── handlers.py   # Обработчики команд и платежей
│   ├── database.py   # SQLite база данных
│   └── config.py     # Конфигурация
├── api/              # REST API (Flask)
│   └── server.py     # Сервер проверки лицензий
├── miniapp/          # Mini App (GitHub Pages)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── .github/workflows/ # CI/CD
├── Dockerfile
├── docker-compose.yml
├── render.yaml       # Render.com деплой
└── requirements.txt
```

## ⚙️ Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | — |
| `ADMIN_IDS` | ID администраторов | 265070804 |
| `API_KEYS` | API ключи (через запятую) | — |
| `API_PORT` | Порт REST API | 8080 |
| `DATABASE_PATH` | Путь к БД SQLite | starspay.db |
| `MINIAPP_URL` | URL Mini App | https://sochiautoparts.github.io/stars-pay-bot/ |

## 📜 Лицензия

MIT
