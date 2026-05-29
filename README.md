# 💎 StarsPay Bot

**Универсальная платформа оплаты через Telegram Stars** — полностью бесплатно, на GitHub.

> 🆓 **Никаких внешних сервисов!** Бот работает 24/7 через GitHub Actions (бесплатно для публичных репозиториев).

## 🌟 Возможности

- 💳 **Оплата Telegram Stars** — встроенная платёжная система Telegram
- 📦 **Мульти-проекты** — один бот для оплаты нескольких проектов
- 🔑 **Лицензионные ключи** — автоматическая генерация и проверка
- 🌐 **Mini App** — красивый веб-интерфейс на GitHub Pages
- 🔗 **Публичный API** — проверка лицензий через GitHub (без сервера!)
- 👥 **Реферальная программа** — бонусы за приглашения
- 👑 **Админ-панель** — статистика и управление
- 🆓 **Полностью бесплатно** — работает на GitHub Actions

## 🏗 Как это работает

```
┌─────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  Пользователь │───▶│  Telegram Bot     │───▶│  GitHub Actions   │
│  в Telegram  │◀───│  @allstarspay_bot │◀───│  (каждые 5 мин)   │
└─────────────┘    └──────────────────┘    └──────────────────┘
                          │                         │
                     Оплата Stars           Обработка платежей
                     Генерация ключа         SQLite + Cache
                                                    │
                                            ┌───────▼──────────┐
                                            │  licenses.json    │
                                            │  (в репозитории)  │
                                            └───────┬──────────┘
                                                    │
                    ┌──────────────────┐    ┌───────▼──────────┐
                    │  GitMoji AI      │◀───│  raw.githubusercontent.com  │
                    │  (проверка ключа)│    │  (публичный API)  │
                    └──────────────────┘    └──────────────────┘
```

**Весь цикл:**
1. Пользователь пишет боту `/start` → видит проекты и тарифы
2. Выбирает тариф → оплачивает Telegram Stars
3. Бот генерирует лицензионный ключ → отправляет в чат
4. Ключ сохраняется в `data/licenses.json` в репозитории
5. GitMoji AI проверяет ключ через публичный URL на GitHub

## 🚀 Настройка (один раз)

### 1. Секреты GitHub

В репозитории `stars-pay-bot` → Settings → Secrets and variables → Actions:

| Секрет | Значение |
|--------|----------|
| `BOT_TOKEN` | Токен от @BotFather |
| `ADMIN_IDS` | Ваш Telegram ID |
| `API_KEYS` | API ключ для проверки лицензий |

### 2. Подключение Mini App

1. Откройте **@BotFather**
2. Отправьте `/newapp`
3. Выберите **@allstarspay_bot**
4. Укажите URL: `https://sochiautoparts.github.io/stars-pay-bot/`

### 3. Всё! Бот запускается автоматически каждые 5 минут.

## 🔗 Проверка лицензий (без сервера!)

Licenses хранятся в публичном файле:
```
https://raw.githubusercontent.com/sochiautoparts/stars-pay-bot/main/data/licenses.json
```

### Python (в любом проекте)

```python
import hashlib, requests, time

def verify_license(key: str) -> bool:
    """Проверка лицензии через GitHub — бесплатно, без сервера."""
    url = "https://raw.githubusercontent.com/sochiautoparts/stars-pay-bot/main/data/licenses.json"
    data = requests.get(url, timeout=10).json()
    key_hash = hashlib.sha256(key.encode()).hexdigest()[:16]
    for lic in data.get("licenses", []):
        if lic.get("key_hash") == key_hash and lic.get("active"):
            if lic.get("expires_at", 0) > 0 and time.time() > lic["expires_at"]:
                return False
            return True
    return False
```

### GitHub Action

```yaml
- name: Verify License
  run: |
    KEY_HASH=$(echo -n "$LICENSE_KEY" | sha256sum | cut -c1-16)
    DATA=$(curl -s https://raw.githubusercontent.com/sochiautoparts/stars-pay-bot/main/data/licenses.json)
    VALID=$(echo "$DATA" | python3 -c "
    import sys, json, time
    data = json.load(sys.stdin)
    key_hash = '$KEY_HASH'
    for lic in data.get('licenses', []):
        if lic.get('key_hash') == key_hash and lic.get('active'):
            if lic.get('expires_at', 0) > 0 and time.time() > lic['expires_at']:
                continue
            print('true')
            sys.exit(0)
    print('false')
    ")
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

## 💰 Продукты по умолчанию

| Проект | Месяц | Год | Навсегда |
|--------|-------|-----|----------|
| GitMoji AI Pro | 149 ⭐ | 999 ⭐ | 2999 ⭐ |

## 📦 Структура проекта

```
stars-pay-bot/
├── bot/              # Telegram Bot (aiogram 3.x)
│   ├── main.py       # Точка входа (с auto-stop)
│   ├── handlers.py   # Обработчики команд и платежей
│   ├── middleware.py  # Обработка ошибок
│   ├── database.py   # SQLite база данных
│   └── config.py     # Конфигурация (env vars)
├── api/              # REST API (Flask)
│   └── server.py     # Сервер проверки лицензий
├── data/             # Публичные данные
│   └── licenses.json # Лицензии (публичный API)
├── miniapp/          # Mini App (GitHub Pages)
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── .github/workflows/
│   ├── run-bot.yml   # 🤖 24/7 бот (каждые 5 мин)
│   ├── deploy.yml    # 🌐 Deploy Mini App (Pages)
│   ├── test-bot.yml  # 🧪 CI тесты
│   └── deploy-bot.yml # 🚀 Render deploy (опция)
├── Dockerfile
├── docker-compose.yml
├── render.yaml       # Альтернатива: Render.com деплой
└── requirements.txt
```

## ⚙️ Переменные окружения

| Переменная | Описание | Обязательная |
|-----------|----------|-------------|
| `BOT_TOKEN` | Токен Telegram бота | ✅ Да |
| `ADMIN_IDS` | ID администраторов | ✅ Да |
| `API_KEYS` | API ключи (через запятую) | ✅ Да |
| `BOT_RUN_SECONDS` | Время работы бота за сессию | Нет (240) |
| `DATABASE_PATH` | Путь к БД SQLite | Нет |
| `MINIAPP_URL` | URL Mini App | Нет |

## 📜 Лицензия

MIT
