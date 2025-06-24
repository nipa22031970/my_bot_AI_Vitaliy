from aiogram.fsm.state import State, StatesGroup


class GptStates(StatesGroup):
    waiting_for_question = State()


class QuizStates(StatesGroup):
    choose_topic = State()
    answer = State()


class TalkStates(StatesGroup):
    figure = State()
    talking = State()
    end = State()
