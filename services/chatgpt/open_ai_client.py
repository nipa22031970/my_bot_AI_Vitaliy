import logging
from openai import AsyncOpenAI, OpenAIError, APITimeoutError, APIConnectionError, AuthenticationError, RateLimitError
from settings.config import config

# Окремий логгер для OpenAI
openai_logger = logging.getLogger("openai")
log_file = config.path_to_logs / "openai.log"
log_file.parent.mkdir(parents=True, exist_ok=True)
if not openai_logger.handlers:
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    openai_logger.addHandler(file_handler)
openai_logger.setLevel(logging.INFO)

class OpenAIClient:
    def __init__(self, openai_api_key: str, model: str, temperature: float):
        self._client = AsyncOpenAI(api_key=openai_api_key)
        self._model = model
        self._temperature = temperature

    async def take_task(self, user_message: str, system_prompt: str) -> str:
        try:
            openai_logger.info(f"[GPT REQUEST] SYSTEM PROMPT:\n{system_prompt}")
            openai_logger.info(f"[GPT REQUEST] USER MESSAGE:\n{user_message}")

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message}
                ],
                temperature=self._temperature
            )
            reply = response.choices[0].message.content
            openai_logger.info(f"[GPT RESPONSE]\n{reply}")
            return reply

        except AuthenticationError as e:
            openai_logger.error(f"Authentication error: {e}")
            return "❌ Помилка авторизації OpenAI API. Перевірте ключ."
        except RateLimitError as e:
            openai_logger.warning(f"Rate limit error: {e}")
            return "⚠️ Перевищено ліміт запитів до OpenAI. Спробуйте пізніше."
        except APITimeoutError as e:
            openai_logger.error(f"Timeout error: {e}")
            return "⏳ Час очікування відповіді від OpenAI вичерпано. Спробуйте ще раз."
        except APIConnectionError as e:
            openai_logger.error(f"Connection error: {e}")
            return "🔌 Проблема з підключенням до OpenAI. Перевірте інтернет."
        except OpenAIError as e:
            openai_logger.error(f"OpenAI error: {e}")
            return "❗ Виникла помилка при зверненні до OpenAI."
        except Exception as e:
            openai_logger.exception(f"Unexpected error: {e}")
            return "🚫 Невідома помилка. Зверніться до адміністратора."