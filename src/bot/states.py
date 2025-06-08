from aiogram.fsm.state import State, StatesGroup

class QuizStates(StatesGroup):
    choose_topic = State()
    answer = State()
class TalkStates(StatesGroup):
    figure = State()    
    talking = State()
    end = State()
