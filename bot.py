import asyncio
import os
import shutil
import tempfile
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile

BOT_TOKEN = "8546598726:AAG2SfBlXi96vtXBGPEQeGNhpXZvyQ-eZj4"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TEMP_DIR = tempfile.mkdtemp()
OUTPUT_DIR = os.path.join(TEMP_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Качество видео
OUTPUT_WIDTH = 640
OUTPUT_HEIGHT = 640
FPS = 30

async def convert_webm_to_video(input_path: str, output_path: str) -> bool:
    """Конвертирует WEBM в MP4"""
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
        await process.communicate()
        return process.returncode == 0
    except:
        return False

async def convert_tgs_to_video(input_path: str, output_path: str) -> bool:
    """Конвертирует TGS (Lottie) в MP4"""
    try:
        import rlottie_python
        import imageio
        import numpy as np
        from PIL import Image

        # Загружаем анимацию
        with open(input_path, "rb") as f:
            data = f.read()
        animation = rlottie_python.LottieAnimation.from_data(data)
        duration = animation.duration() / 1000.0  # миллисекунды -> секунды
        fps = 30
        total_frames = int(duration * fps)

        frames = []
        for i in range(total_frames):
            frame = animation.render(i / fps)
            img = Image.fromarray(frame, "RGBA")
            frames.append(np.array(img))

        # Сохраняем как временный GIF
        gif_path = output_path.replace(".mp4", ".gif")
        imageio.mimsave(gif_path, frames, fps=fps, loop=0)

        # Конвертируем GIF в MP4
        cmd = [
            "ffmpeg", "-y",
            "-i", gif_path,
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
        await process.communicate()
        os.remove(gif_path)
        return process.returncode == 0
    except Exception as e:
        print("TGS error:", e)
        return False

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Пришли мне премиум-эмодзи или анимированный стикер — я сделаю из него видео!")

@dp.message()
async def handle_media(message: types.Message):
    # Проверяем, есть ли анимированный стикер
    if message.sticker and (message.sticker.is_animated or message.sticker.is_video):
        sticker = message.sticker
        ext = ".webm" if sticker.is_video else ".tgs"
        input_path = os.path.join(TEMP_DIR, f"{sticker.file_unique_id}{ext}")
        output_path = os.path.join(OUTPUT_DIR, f"{sticker.file_unique_id}.mp4")

        file = await bot.get_file(sticker.file_id)
        await bot.download_file(file.file_path, input_path)

        processing = await message.answer("Конвертирую...")
        if sticker.is_video:
            success = await convert_webm_to_video(input_path, output_path)
        else:
            success = await convert_tgs_to_video(input_path, output_path)

        if success:
            video = FSInputFile(output_path)
            await message.answer_video(video, caption="Готово!")
        else:
            await message.answer("Не удалось сконвертировать стикер.")

        await processing.delete()
        os.remove(input_path)
        os.remove(output_path)
        return

    # Проверяем, есть ли кастомный эмодзи в тексте
    if message.entities:
        custom_emoji = [e for e in message.entities if e.type == "custom_emoji"]
        if custom_emoji:
            emoji_id = custom_emoji[0].custom_emoji_id
            stickers = await bot.get_custom_emoji_stickers([emoji_id])
            if stickers:
                sticker = stickers[0]
                ext = ".webm" if sticker.is_video else ".tgs"
                input_path = os.path.join(TEMP_DIR, f"{emoji_id}{ext}")
                output_path = os.path.join(OUTPUT_DIR, f"{emoji_id}.mp4")

                file = await bot.get_file(sticker.file_id)
                await bot.download_file(file.file_path, input_path)

                processing = await message.answer("Конвертирую эмодзи...")
                if sticker.is_video:
                    success = await convert_webm_to_video(input_path, output_path)
                else:
                    success = await convert_tgs_to_video(input_path, output_path)

                if success:
                    video = FSInputFile(output_path)
                    await message.answer_video(video, caption="Готово!")
                else:
                    await message.answer("Не удалось сконвертировать эмодзи.")

                await processing.delete()
                os.remove(input_path)
                os.remove(output_path)
                return

    await message.answer("Пожалуйста, отправьте премиум-эмодзи или анимированный стикер (WEBM/TGS).")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
