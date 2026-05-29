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

## 🚀 Быстрый старт — Deploy на Render.com

**Render.com** — бесплатный хостинг для бота (24/7). Деплой за 3 минуты:

### Шаг 1: Регистрация
1. Перейдите на [render.com](https://render.com)
2. Зарегистрируйтесь через GitHub

### Шаг 2: Создание сервиса
1. Нажмите **New** → **Web Service**
2. Подключите репозиторий `sochiautoparts/stars-pay-bot`
3. Или нажмите кнопку:
   [![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/sochiautoparts/stars-pay-bot)

### Шаг 3: Настройка переменных
Установите следующие **Environment Variables**:

| Переменная | Значение |
|-----------|----------|
| `BOT_TOKEN` | Токен от @BotFather |
| `ADMIN_IDS` | Ваш Telegram ID |
| `API_KEYS` | API ключ (например: `sk_starspay_xxx`) |
| `DATABASE_PATH` | `/opt/render/project/src/data/starspay.db` |

### Шаг 4: Deploy
Нажмите **Create Web Service**. Бот запустится автоматически!

## 🌐 Mini App

Mini App доступен по адресу: **https://sochiautoparts.github.io/stars-pay-bot/**

### Подключение к боту:
1. Откройте **@BotFather**
2. Отправьте `/newapp`
3. Выберите **@allstarspay_bot**
4. Укажите:
   - **Title**: `StarsPay`
   - **Description**: `Магазин подписок`
   - **URL**: `https://sochiautoparts.github.io/stars-pay-bot/`

## 🔗 REST API

После деплоя на Render ваш API будет доступен по адресу:
`https://starspay-bot.onrender.com` (или ваш кастомный URL)

### Проверка лицензии

```bash
curl -X POST https://starspay-bot.onrender.com/api/v1/verify \
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
curl -X POST https://starspay-bot.onrender.com/api/v1/check \
  -H "X-API-Key: ваш_api_key" \
  -H "Content-Type: application/json" \
  -d '{"user_id": 12345, "project": "gitmoji-ai"}'
```

### Список проектов

```bash
curl https://starspay-bot.onrender.com/api/v1/projects
```

## 🔧 Интеграция с проектами

### Python (GitMoji AI)

```python
import requests

STARSPAY_API = "https://starspay-bot.onrender.com"
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
    VALID=$(curl -s -X POST https://starspay-bot.onrender.com/api/v1/verify \
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
│   ├── middleware.py  # Обработка ошибок
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

| Переменная | Описание | Обязательная |
|-----------|----------|-------------|
| `BOT_TOKEN` | Токен Telegram бота | ✅ Да |
| `ADMIN_IDS` | ID администраторов | ✅ Да |
| `API_KEYS` | API ключи (через запятую) | ✅ Да |
| `PORT` | Порт REST API (Render) | Нет (8080) |
| `DATABASE_PATH` | Путь к БД SQLite | Нет |
| `MINIAPP_URL` | URL Mini App | Нет |

## 📜 Лицензия

MIT
