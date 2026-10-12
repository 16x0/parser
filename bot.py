import asyncio
import logging
import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)
from analyzer import LotAnalysis
from config import config
from scanner import MarketScanner
import uvicorn
import server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("bot")

router = Router()
scanner: MarketScanner

def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура с кнопкой WebApp и управления."""
    buttons = []
    if config.WEBAPP_URL and config.WEBAPP_URL.startswith("https://"):
        buttons.append([
            InlineKeyboardButton(
                text="⚡ Открыть MRKT Radar",
                web_app=WebAppInfo(url=config.WEBAPP_URL),
            )
        ])
    else:
        buttons.append([
            InlineKeyboardButton(
                text="⚡ Открыть маркет",
                url="https://t.me/mrkt",
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="📊 Статус сканера", callback_data="status"),
        InlineKeyboardButton(text="⚙️ Фильтры спреда", callback_data="filters"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start: регистрация пользователя и приветствие."""
    scanner.add_subscriber(message.chat.id)
    
    welcome_text = (
        "👋 <b>Добро пожаловать в MRKT Radar & Flipper!</b>\n\n"
        "Я отслеживаю новые лоты и моментальные сливы подарков в реальном времени, "
        "вычисляю чистый спред за вычетом комиссии и присылаю уведомления.\n\n"
        f"🎯 <b>Текущий порог спреда:</b> <code>≥ {config.MIN_SPREAD_PERCENT}%</code>\n"
        f"⏱ <b>Интервал опроса:</b> <code>{config.POLL_INTERVAL_SECONDS} сек</code>\n"
        f"💼 <b>Учет комиссии MRKT:</b> <code>{config.MARKET_FEE_PERCENT}%</code>\n\n"
        "Нажмите кнопку ниже, чтобы открыть терминал в виде <b>Web App</b>:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

@router.message(Command("status"))
@router.callback_query(F.data == "status")
async def show_status(event: Message | CallbackQuery):
    """Отображение состояния сканера и закэшированных цен."""
    active_count = len(scanner.subscribers)
    floors_text = "\n".join([f"• <b>{col}:</b> <code>{p} TON</code>" for col, p in scanner.floor_cache.items()]) or "<i>Кэш формируется...</i>"

    status_text = (
        "📊 <b>Статус сканера MRKT:</b>\n\n"
        f"• <b>Состояние:</b> {'🟢 Работает' if scanner.is_running else '🔴 Остановлен'}\n"
        f"• <b>Активных подписчиков:</b> {active_count}\n"
        f"• <b>Отслежено уникальных лотов:</b> {len(scanner.seen_lots)}\n\n"
        f"📈 <b>Текущие Floor Prices:</b>\n{floors_text}"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(status_text, reply_markup=get_main_keyboard())
        await event.answer()
    else:
        await event.answer(status_text, reply_markup=get_main_keyboard())

@router.callback_query(F.data == "filters")
async def show_filters(callback: CallbackQuery):
    """Интерактивное меню изменения минимального спреда."""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="15%", callback_data="set_spread_15"),
                InlineKeyboardButton(text="20%", callback_data="set_spread_20"),
                InlineKeyboardButton(text="25%", callback_data="set_spread_25"),
                InlineKeyboardButton(text="30%", callback_data="set_spread_30"),
            ],
            [InlineKeyboardButton(text="« Назад", callback_data="status")],
        ]
    )
    await callback.message.edit_text(
        f"⚙️ <b>Настройка порога спреда:</b>\n\n"
        f"Текущее значение: <b>{config.MIN_SPREAD_PERCENT}%</b>\n"
        "Выберите минимальную чистую прибыль для получения алертов:",
        reply_markup=kb,
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_spread_"))
async def set_spread(callback: CallbackQuery):
    """Установка нового значения спреда."""
    val = float(callback.data.split("_")[-1])
    config.MIN_SPREAD_PERCENT = val
    await callback.answer(f"Порог изменен на {val}%")
    await show_status(callback)

async def send_lot_alert(bot: Bot, analysis: LotAnalysis):
    """Рассылка уведомления о выгодном лоте всем активным пользователям."""
    num_str = f" #{analysis.number}" if analysis.number else ""
    lucky_badge = " 🎯 <b>[Красивый номер]</b>" if analysis.is_lucky_number else ""
    
    attrs_str = ""
    if analysis.attributes:
        attrs_str = "\n💎 <b>Атрибуты:</b> " + ", ".join(analysis.attributes)

    alert_text = (
        f"🔥 <b>СНАЙПЕР-АЛЕРТ: {analysis.collection_name}{num_str}</b>{lucky_badge}\n\n"
        f"💰 <b>Цена покупки:</b> <code>{analysis.buy_price} TON</code>\n"
        f"📊 <b>Текущий флор:</b> <code>{analysis.floor_price} TON</code>\n"
        f"🟢 <b>Чистая прибыль (-5%):</b> <code>+{analysis.net_profit} TON (+{analysis.roi_percent}% ROI)</code>"
        f"{attrs_str}\n"
    )

    action_buttons = [InlineKeyboardButton(text="⚡ Купить на MRKT", url=analysis.deep_link)]
    if config.WEBAPP_URL and config.WEBAPP_URL.startswith("https://"):
        action_buttons.append(InlineKeyboardButton(text="📊 В Radar TMA", web_app=WebAppInfo(url=config.WEBAPP_URL)))

    kb = InlineKeyboardMarkup(inline_keyboard=[action_buttons])

    for chat_id in scanner.subscribers:
        try:
            await bot.send_message(chat_id, alert_text, reply_markup=kb)
        except Exception as e:
            logger.warning(f"Не удалось отправить алерт в чат {chat_id}: {e}")

async def main():
    if not config.BOT_TOKEN:
        logger.error(
            "ОШИБКА: BOT_TOKEN не указан в файле .env! "
            "Получите токен у @BotFather и укажите его в .env"
        )
        return

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Инициализация сканера
    global scanner
    scanner = MarketScanner(
        on_alert_callback=lambda lot: send_lot_alert(bot, lot)
    )

    # Запуск сервера WebApp
    server.scanner_instance = scanner
    uvi_config = uvicorn.Config(server.app, host=config.HOST, port=config.PORT, log_level="warning")
    uvi_server = uvicorn.Server(uvi_config)
    server_task = asyncio.create_task(uvi_server.serve())

    logger.info(f"Запуск Telegram-бота, парсера и WebApp сервера на http://{config.HOST}:{config.PORT}...")

    # Запускаем параллельно фоновый цикл парсера и поллинг бота
    scanner_task = asyncio.create_task(scanner.run())
    try:
        await dp.start_polling(bot)
    finally:
        scanner.stop()
        scanner_task.cancel()
        uvi_server.should_exit = True
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот завершил работу.")
