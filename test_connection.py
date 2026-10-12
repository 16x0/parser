import asyncio
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
import httpx
from aiogram import Bot
from config import config
from mrkt_client import MRKTClient

async def test():
    print("--- 1. Тестирование Telegram Бота ---")
    bot = Bot(token=config.BOT_TOKEN)
    try:
        me = await bot.get_me()
        print(f"✅ Telegram Бот подключен! Имя: @{me.username} ({me.first_name})")
        
        if config.DEFAULT_CHAT_ID:
            print(f"Отправка тестового приветствия в чат {config.DEFAULT_CHAT_ID}...")
            await bot.send_message(
                chat_id=config.DEFAULT_CHAT_ID,
                text="🚀 <b>MRKT Radar успешно подключен!</b>\n\nПарсер готов к работе и отслеживанию подарков.",
                parse_mode="HTML"
            )
            print("✅ Сообщение успешно доставлено пользователю!")
    except Exception as e:
        print(f"❌ Ошибка Telegram бота: {e}")
    finally:
        await bot.session.close()

    print("\n--- 2. Тестирование API MRKT ---")
    async with MRKTClient() as client:
        try:
            res = await client.get_fresh_listings(count=5)
            print(f"✅ Ответ от MRKT API получен! Найдено подарков в выдаче: {len(res)}")
            for idx, g in enumerate(res[:5], 1):
                name = g.get('collectionName') or g.get('name') or 'Gift'
                raw_p = g.get('salePrice') or g.get('price') or 0
                price = raw_p / 1e9 if raw_p > 1e6 else raw_p
                num = g.get('number')
                floor_raw = g.get('floorPriceNanoTONsByCollection') or 0
                floor = floor_raw / 1e9 if floor_raw > 1e6 else floor_raw
                print(f"   {idx}. {name} #{num} — Цена: {price:.2f} TON (Флор: {floor:.2f} TON)")
        except Exception as e:
            print(f"❌ Ошибка запроса к MRKT API: {e}")

if __name__ == "__main__":
    asyncio.run(test())
