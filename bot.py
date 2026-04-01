import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

BOT_TOKEN = "8546598726:AAG2SfBlXi96vtXBGPEQeGNhpXZvyQ-eZj4"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Отправьте GIF — я верну его в виде документа (без изменений).")

@dp.message(lambda msg: msg.document and msg.document.mime_type == "image/gif")
async def handle_gif_document(message: types.Message):
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    input_path = f"/tmp/{file_id}.gif"
    await bot.download_file(file.file_path, input_path)

    # Отправляем как документ (GIF)
    doc = FSInputFile(input_path, filename=message.document.file_name or "animation.gif")
    await message.answer_document(doc, caption="Вот ваш GIF")

    os.remove(input_path)

@dp.message(lambda msg: msg.animation)
async def handle_animation(message: types.Message):
    # Если прислали анимацию (GIF, но Telegram считает её анимацией)
    file_id = message.animation.file_id
    file = await bot.get_file(file_id)
    input_path = f"/tmp/{file_id}.mp4"  # анимация приходит в mp4
    await bot.download_file(file.file_path, input_path)

    # Пересылаем как документ
    doc = FSInputFile(input_path, filename="animation.mp4")
    await message.answer_document(doc, caption="Вот ваша анимация в формате MP4")

    os.remove(input_path)

@dp.message()
async def unknown(message: types.Message):
    await message.answer("Пожалуйста, отправьте GIF-файл.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
