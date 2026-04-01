import asyncio
import os
import tempfile
import imageio
import numpy as np
from PIL import Image
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
import concurrent.futures

BOT_TOKEN = "8546598726:AAG2SfBlXi96vtXBGPEQeGNhpXZvyQ-eZj4"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

BOT_VERSION = "v2.0"
BOT_UPDATE_TEXT = "✅ Обновление: полный отказ от ffmpeg, обработка GIF через Python (imageio + Pillow)."

TEMP_DIR = tempfile.mkdtemp()
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 816
MAX_FRAMES = 150
MAX_SIZE_MB = 5
TIMEOUT = 40

def get_gif_info(input_path):
    try:
        reader = imageio.get_reader(input_path, format='gif')
        frames = reader.get_length()
        size_mb = os.path.getsize(input_path) / (1024 * 1024)
        reader.close()
        return frames, size_mb
    except:
        return None, None

def resize_gif(input_path: str, output_path: str) -> bool:
    try:
        reader = imageio.get_reader(input_path, format='gif')
        metadata = reader.get_meta_data()
        fps = metadata.get('fps', 15)
        frames = []
        for i, frame in enumerate(reader):
            if i >= MAX_FRAMES:
                break
            img = Image.fromarray(frame)
            img.thumbnail((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.LANCZOS)
            new_img = Image.new('RGB', (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0))
            x = (OUTPUT_WIDTH - img.width) // 2
            y = (OUTPUT_HEIGHT - img.height) // 2
            new_img.paste(img, (x, y))
            frames.append(np.array(new_img))
        reader.close()

        writer = imageio.get_writer(output_path, format='gif', mode='I', fps=fps)
        for frame in frames:
            writer.append_data(frame)
        writer.close()
        return True
    except Exception as e:
        print(f"Resize GIF error: {e}")
        return False

async def run_with_timeout(func, *args, timeout=TIMEOUT):
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        try:
            result = await asyncio.wait_for(loop.run_in_executor(pool, func, *args), timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"🤖 Бот версии {BOT_VERSION}\n\n{BOT_UPDATE_TEXT}\n\nОтправь GIF — я сделаю из него широкоформатный GIF 1920×816 с чёрными полями.\nОбрабатываются GIF до 150 кадров и до 5 МБ. Если больше — верну исходный.")

@dp.message(lambda msg: msg.document and msg.document.mime_type == "image/gif")
async def handle_gif_document(message: types.Message):
    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    input_path = os.path.join(TEMP_DIR, f"{file_id}.gif")
    output_path = os.path.join(TEMP_DIR, f"{file_id}_wide.gif")

    await bot.download_file(file.file_path, input_path)

    frames, size_mb = get_gif_info(input_path)
    if frames is None:
        await message.answer("Не удалось прочитать GIF. Отправляю исходный.")
        original = FSInputFile(input_path, filename="animation.gif")
        await message.answer_animation(original)
        os.remove(input_path)
        return

    if frames > MAX_FRAMES:
        await message.answer(f"GIF содержит {frames} кадров (максимум {MAX_FRAMES}). Отправляю исходный.")
        original = FSInputFile(input_path, filename="animation.gif")
        await message.answer_animation(original)
        os.remove(input_path)
        return

    if size_mb > MAX_SIZE_MB:
        await message.answer(f"GIF слишком большой ({size_mb:.1f} МБ, максимум {MAX_SIZE_MB}). Отправляю исходный.")
        original = FSInputFile(input_path, filename="animation.gif")
        await message.answer_animation(original)
        os.remove(input_path)
        return

    processing = await message.answer(f"Обрабатываю GIF ({frames} кадров)... до {TIMEOUT} сек")
    success = await run_with_timeout(resize_gif, input_path, output_path, timeout=TIMEOUT)

    if success and os.path.exists(output_path):
        gif_file = FSInputFile(output_path, filename="wide_animation.gif")
        await message.answer_animation(gif_file, caption="Готово! Широкоформатный GIF")
        await processing.delete()
    else:
        await processing.edit_text("Обработка не удалась. Отправляю исходный GIF.")
        original = FSInputFile(input_path, filename="animation.gif")
        await message.answer_animation(original)

    for f in (input_path, output_path):
        if os.path.exists(f):
            os.remove(f)

@dp.message(lambda msg: msg.animation)
async def handle_animation(message: types.Message):
    file_id = message.animation.file_id
    file = await bot.get_file(file_id)
    input_path = os.path.join(TEMP_DIR, f"{file_id}.mp4")
    await bot.download_file(file.file_path, input_path)

    await message.answer("Анимации в формате MP4 не обрабатываются. Отправляю исходную.")
    original = FSInputFile(input_path, filename="animation.mp4")
    await message.answer_animation(original)
    os.remove(input_path)

@dp.message()
async def unknown(message: types.Message):
    await message.answer("Отправь GIF-файл.")

async def main():
    print(f"🚀 Бот запущен. Версия: {BOT_VERSION}")
    print(BOT_UPDATE_TEXT)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
