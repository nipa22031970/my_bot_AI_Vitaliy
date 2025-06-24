import json
import aiofiles
from pathlib import Path
from settings.config import config


def file_exists(path: Path) -> bool:
    return path.exists() and path.is_file()


async def load_message(name: str) -> str:
    path = config.path_to_messages / f'{name}.txt'
    if not file_exists(path):
        return f"⚠️ Файл повідомлення '{name}.txt' не знайдено."
    try:
        async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
            return await file.read()
    except Exception as e:
        return f"⚠️ Помилка читання файлу '{name}.txt': {e}"


async def load_image(name: str) -> bytes:
    path = config.path_to_images / f'{name}.jpg'
    if not file_exists(path):
        raise FileNotFoundError(f"Зображення '{name}.jpg' не знайдено.")
    try:
        async with aiofiles.open(path, mode='rb') as file:
            return await file.read()
    except Exception as e:
        raise RuntimeError(f"Помилка читання зображення '{name}.jpg': {e}")


async def load_menu(name: str) -> dict:
    path = config.path_to_menus / f'{name}.json'
    if not file_exists(path):
        return {}
    try:
        async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
            return json.loads(await file.read())
    except Exception:
        return {}


async def load_prompt(name: str) -> str:
    path = config.path_to_prompts / f'{name}.txt'
    if not file_exists(path):
        return f"⚠️ Файл prompt '{name}.txt' не знайдено."
    try:
        async with aiofiles.open(path, mode='r', encoding='utf-8') as file:
            return await file.read()
    except Exception as e:
        return f"⚠️ Помилка читання prompt '{name}.txt': {e}"
