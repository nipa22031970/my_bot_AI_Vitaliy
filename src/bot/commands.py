from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
import html
import random

from src.bot.states import (
    GptStates,
    TalkStates,
    QuizStates,
)
from src.bot.resource_loader import load_message, load_prompt, load_image
from src.bot.keyboards import get_talk_keyboard
from services.chatgpt.open_ai_client import OpenAIClient
from src.db.repository import GptSessionRepository
from src.db.enums import SessionMode
from src.bot.message_sender import show_menu

router = Router()


# --- Inline кнопки для TALK ---
@router.callback_query(lambda c: c.data == "talk_continue")
async def talk_continue_callback(
    callback: types.CallbackQuery, state: FSMContext
):
    await callback.answer()
    await callback.message.answer(
        "Задайте наступне питання або напишіть текст."
    )


@router.callback_query(lambda c: c.data == "talk_end")
async def talk_end_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer(
        "Дякую за розмову! Ви повернулись у головне меню."
    )


@router.message(F.text == "/start")
async def start_handler(message: types.Message, bot: Bot):
    try:
        with open("resources/images/avatar_main.jpg", "rb") as img:
            image_bytes = img.read()
        await send_image_bytes(
            message, image_bytes, image_name="avatar_main.jpg"
        )
    except Exception:
        await send_html_message(
            message, "👋 Привет! Я бот (фото не найдено)."
        )

    text = await load_message("main")
    await send_html_message(message, text)

    commands = [
        {"command": "start", "description": "Головне меню бота"},
        {"command": "random", "description": "Випадковий факт · 🧠"},
        {"command": "gpt", "description": "Питання ChatGPT · 🤖"},
        {"command": "talk", "description": "Діалог з особистістю · 👤"},
        {"command": "quiz", "description": "Перевірити знання ❓"},
    ]
    await show_menu(bot, message.chat.id, commands)


@router.message(F.text == "/random")
async def random_fact(message: types.Message):
    try:
        with open("resources/messages/random.txt", encoding="utf-8") as f:
            facts = [line.strip() for line in f if line.strip()]
        fact = random.choice(facts) if facts else "Фактів немає."
    except Exception:
        fact = "Фактів немає."
    await message.answer(fact)


async def ask_openai_and_send(
    message: types.Message,
    openai_client: OpenAIClient,
    user_message: str,
    system_prompt: str,
    send_long: bool = False
):
    reply = await openai_client.take_task(
        user_message=user_message,
        system_prompt=system_prompt
    )
    if not reply:
        reply = (
            "⚠️ Відповідь від OpenAI не отримана. "
            "Спробуйте ще раз або зверніться до адміністратора."
        )
    if send_long:
        await send_long_message(
            message,
            html.escape(reply),
            parse_mode=ParseMode.HTML
        )
    else:
        await send_html_message(message, reply)


async def send_long_message(
    message: types.Message,
    text: str,
    parse_mode: str = ParseMode.HTML
):
    max_length = 4096
    for i in range(0, len(text), max_length):
        chunk = text[i:i + max_length]
        await message.answer(chunk, parse_mode=parse_mode)


async def send_html_message(message: types.Message, text: str):
    await message.answer(text, parse_mode=ParseMode.HTML)


async def send_image_bytes(
    message: types.Message,
    image_bytes: bytes,
    image_name: str = "image.jpg",
    caption: str | None = None,
    parse_mode: str = "HTML"
):
    await message.answer_photo(
        BufferedInputFile(image_bytes, filename=image_name),
        caption=caption,
        parse_mode=parse_mode
    )


# --- GPT ---

@router.message(F.text == "/gpt")
async def gpt_entry(message: types.Message, state: FSMContext):
    text = await load_message("gpt")
    await send_html_message(message, text)
    await state.set_state(GptStates.waiting_for_question)


@router.message(GptStates.waiting_for_question)
async def gpt_reply(
    message: types.Message,
    state: FSMContext,
    openai_client: OpenAIClient,
    session_repository: GptSessionRepository
):
    await send_html_message(message, "⏳ Обробляю запит...")

    user_id = message.from_user.id
    session_id = await session_repository.get_or_create_session(
        user_id, SessionMode.GPT
    )

    user_text = message.text.strip()
    await session_repository.add_message(
        session_id, role="user", content=user_text
    )

    system_prompt = await load_prompt("gpt")
    await ask_openai_and_send(
        message, openai_client, user_text, system_prompt
    )
    await state.clear()


# --- TALK ---

@router.message(F.text == "/talk")
async def talk_to_figure(message: types.Message, state: FSMContext):
    await state.set_state(TalkStates.figure)
    text = await load_message("talk")
    image_bytes = await load_image("talk")
    persons_list = ['cobain', 'hawking', 'nietzsche', 'queen', 'tolkien']
    persons_text = 'Введіть особистість: ' + ', '.join(persons_list)
    await send_image_bytes(message=message, image_bytes=image_bytes)
    await send_html_message(message=message, text=text)
    await send_html_message(message=message, text=persons_text)


@router.message(TalkStates.figure)
async def set_figure(message: types.Message, state: FSMContext):
    from settings.config import config

    if not isinstance(message.text, str) or not message.text.strip():
        await message.answer(
            "⚠️ Ви не ввели ім'я особистості. Спробуйте ще раз."
        )
        return

    prompt_path = config.path_to_prompts / (
        f"talk_{message.text.strip().lower()}.txt"
    )

    if not prompt_path.exists():
        text = await load_message("talk_not_found")
        await message.answer(text)
        return
    prompt = await load_prompt(f"talk_{message.text.strip().lower()}")
    await state.update_data(
        system_prompt=prompt,
        figure=message.text.strip().lower()
    )
    await state.set_state(TalkStates.talking)

    image_name = f"talk_{message.text.strip().lower()}"
    image_bytes = await load_image(image_name)

    text = 'Задай своє запитання: '
    await send_image_bytes(message=message, image_bytes=image_bytes)
    await send_html_message(message=message, text=text)


@router.message(TalkStates.talking)
async def talk(
    message: types.Message,
    state: FSMContext,
    openai_client: OpenAIClient,
    session_repository: GptSessionRepository
):
    user_input = message.text.strip().lower()
    user_id = message.from_user.id
    data = await state.get_data()
    system_prompt = data.get("system_prompt")
    session_id = await session_repository.get_or_create_session(
        user_id,
        SessionMode.TALK
    )
    await session_repository.add_message(
        session_id, role='user', content=user_input
    )
    await ask_openai_and_send(
        message, openai_client, user_input, system_prompt, send_long=True
    )

    keyboard = await get_talk_keyboard()
    await message.answer(
        text=await load_message("talk_next_action"),
        reply_markup=keyboard
    )


# --- QUIZ ---

@router.message(F.text == "/quiz")
async def quiz_entry(message: types.Message, state: FSMContext):
    await quiz_handler(message, state)


@router.message(Command("quiz"))
async def quiz_handler(message: types.Message, state: FSMContext):
    prompt = await load_prompt("quiz")
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="quiz_prog")],
            [KeyboardButton(text="quiz_math")],
            [KeyboardButton(text="quiz_biology")],
        ],
        resize_keyboard=True
    )
    await send_html_message(message, prompt)
    await message.answer("Оберіть тему квізу:", reply_markup=keyboard)
    await state.set_state(QuizStates.choose_topic)


@router.message(QuizStates.choose_topic)
async def quiz_choose_topic(
    message: Message,
    state: FSMContext,
    openai_client: OpenAIClient,
    session_repository: GptSessionRepository
):
    topic = message.text.strip()
    if topic not in ["quiz_prog", "quiz_math", "quiz_biology"]:
        await message.answer(
            "Будь ласка, оберіть одну з тем за допомогою кнопок."
        )
        return

    system_prompt = await load_prompt("quiz")
    user_id = message.from_user.id
    session_id = await session_repository.get_or_create_session(
        user_id, SessionMode.GPT
    )
    await session_repository.add_message(
        session_id, role="user", content=topic
    )

    question = await openai_client.take_task(
        user_message=topic, system_prompt=system_prompt
    )
    await session_repository.add_message(
        session_id, role="system", content=question
    )

    await message.answer(f"Питання по темі:\n\n{question}")
    await state.set_state(QuizStates.answer)
    await state.update_data(quiz_topic=topic, quiz_question=question)


@router.message(QuizStates.answer)
async def quiz_answer(
    message: Message,
    state: FSMContext,
    openai_client: OpenAIClient,
    session_repository: GptSessionRepository
):
    data = await state.get_data()
    user_answer = message.text.strip()
    quiz_question = data.get("quiz_question")
    system_prompt = await load_prompt("quiz")

    check_prompt = (
        f"Питання: {quiz_question}\n"
        f"Відповідь користувача: {user_answer}\n"
        f"Чи правильна відповідь? Відповідай як у інструкції."
    )
    reply = await openai_client.take_task(
        user_message=check_prompt,
        system_prompt=system_prompt
    )
    await message.answer(reply)
