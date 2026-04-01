import asyncio
import os
import subprocess
import tempfile
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

BOT_TOKEN = "8546598726:AAG2SfBlXi96vtXBGPEQeGNhpXZvyQ-eZj4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TEMP_DIR = tempfile.mkdtemp()

# Настройки видео (как в прошлом коде)
OUTPUT_WIDTH = 640
OUTPUT_HEIGHT = 640
FPS = 30

async def convert_gif_to_video(input_path: str, output_path: str) -> bool:
    """Конвертирует GIF в MP4 с помощью ffmpeg"""
    try:
        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-vf", f"scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:force_original_aspect_ratio=decrease,pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2",
            "-r", str(FPS),
            "-movflags", "+faststart",
            output_path
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            print("FFmpeg error:", stderr.decode())
        return process.returncode == 0
    except Exception as e:
        print("Conversion error:", e)
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Пришли мне GIF — я сделаю из него видео MP4!")

@dp.message(lambda msg: msg.document and msg.document.mime_type == "image/gif")
async def handle_gif_document(message: types.Message):
    # Получаем GIF как документ
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    input_path = os.path.join(TEMP_DIR, f"{file_id}.gif")
    output_path = os.path.join(TEMP_DIR, f"{file_id}.mp4")

    # Скачиваем
    await bot.download_file(file.file_path, input_path)

    processing = await message.answer("Конвертирую GIF в видео...")
    success = await convert_gif_to_video(input_path, output_path)

    if success:
        video = FSInputFile(output_path)
        await message.answer_video(video, caption="Готово!")
    else:
        await message.answer("Не удалось сконвертировать GIF. Убедитесь, что файл корректен.")

    await processing.delete()
    # Удаляем временные файлы
    os.remove(input_path)
    if os.path.exists(output_path):
        os.remove(output_path)

@dp.message(lambda msg: msg.animation)
async def handle_animation(message: types.Message):
    # Если прислали анимацию (GIF в Telegram)
    file_id = message.animation.file_id
    file = await bot.get_file(file_id)
    input_path = os.path.join(TEMP_DIR, f"{file_id}.mp4")  # Telegram хранит анимацию как MP4
    output_path = os.path.join(TEMP_DIR, f"{file_id}_out.mp4")

    await bot.download_file(file.file_path, input_path)

    processing = await message.answer("Конвертирую анимацию в видео...")
    # Анимация уже MP4, просто перекодируем под нужный размер
    success = await convert_gif_to_video(input_path, output_path)

    if success:
        video = FSInputFile(output_path)
        await message.answer_video(video, caption="Готово!")
    else:
        await message.answer("Не удалось сконвертировать анимацию.")

    await processing.delete()
    os.remove(input_path)
    if os.path.exists(output_path):
        os.remove(output_path)

@dp.message()
async def unknown(message: types.Message):
    await message.answer("Отправьте GIF файл или анимацию (через документ или как GIF в Telegram).")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
