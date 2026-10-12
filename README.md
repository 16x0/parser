# MRKT Radar & Flipper Bot 🚀

Телеграм-бот и Telegram Mini App (TMA) для снайпинга и флиппинга подарков (Telegram Gifts / NFTs) на маркетплейсе **MRKT**.

---

## ⚡ Особенности

* **Автоматический расчет чистого спреда:** мгновенное вычисление ROI с автоматическим вычетом комиссии платформы (5%).
* **Детектор редких атрибутов и номеров:** распознавание Low Mint (#1–#100), одинаковых цифр (#777, #999), зеркалок и редких моделей (Albino и др.).
* **Apple HIG & Telegram Core Web App:** минималистичный и функциональный интерфейс с карточками лотов, стаканом (Floor Gaps) и трекером PnL.
* **Мгновенные алерты:** рассылка уведомлений в личные сообщения с прямой deep-link кнопкой выкупа в 1 клик на MRKT.

---

## 📁 Структура проекта

```text
mrkt-bot/
├── webapp/
│   └── index.html       # Нативный Telegram WebApp интерфейс (Apple HIG)
├── analyzer.py          # Логика скоринга, расчет спреда и красивых номеров
├── bot.py               # Основной Telegram-бот на Aiogram 3.x
├── config.py            # Конфигурация и переменные окружения
├── mrkt_client.py       # Асинхронный HTTP-клиент к API маркетплейса
├── scanner.py           # Фоновый воркер опроса и кэширования Floor Price
├── server.py            # Сервер FastAPI для отдачи WebApp
├── requirements.txt     # Python зависимости
└── .env.example         # Пример конфигурации
```

---

## 🛠 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка окружения

Скопируйте `.env.example` в `.env`:

```bash
cp .env.example .env
```

Заполните переменные:
1. `BOT_TOKEN`: получите токен у [@BotFather](https://t.me/BotFather).
2. `MRKT_AUTH_TOKEN`: токен авторизации MRKT (откройте WebApp маркета в браузере с `F12 -> Network`, найдите запрос к `api.tgmrkt.io` и скопируйте заголовок `Authorization`).
3. `WEBAPP_URL`: ссылка на ваш WebApp.

---

### 3. Запуск

Запуск бота и парсера:

```bash
python bot.py
```

Запуск локального сервера WebApp (в отдельном терминале):

```bash
python server.py
```

Для того чтобы WebApp открывался внутри Telegram с вашего компьютера, пробросьте локальный порт 8000 через HTTPS (например, через `ngrok http 8000` или Cloudflare Tunnel) и укажите полученный URL в `.env` (`WEBAPP_URL`) и в настройках бота через `@BotFather`.
