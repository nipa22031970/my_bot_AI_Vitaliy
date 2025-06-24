import aiosqlite
from typing import Optional
import logging


class GptSessionRepository:
    def __init__(self, db_path: str):
        self.db_path = str(db_path)

    async def get_or_create_session(
        self, tg_user_id: int, mode: str
    ) -> Optional[int]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT id FROM gpt_sessions WHERE tg_user_id = ? "
                    "AND mode = ?",
                    (tg_user_id, mode)
                )
                result = await cursor.fetchone()
                await cursor.close()
                if result:
                    return result[0]

                cursor = await conn.execute(
                    "INSERT INTO gpt_sessions (tg_user_id, mode) "
                    "VALUES (?, ?)",
                    (tg_user_id, mode)
                )
                await conn.commit()
                session_id = cursor.lastrowid
                await cursor.close()
                return session_id
        except Exception as e:
            logging.exception(
                f"Ошибка при получении/создании сессии для пользователя "
                f"{tg_user_id}: {e}"
            )
            return None

    async def add_message(
        self, session_id: int, role: str, content: str
    ) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "INSERT INTO gpt_messages (session_id, role, content) "
                    "VALUES (?, ?, ?)",
                    (session_id, role, content)
                )
                await conn.commit()
        except Exception as e:
            logging.exception(
                f"Ошибка при добавлении сообщения в сессию {session_id}: {e}"
            )

    async def get_messages(self, session_id: int) -> list[dict]:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT role, content FROM gpt_messages "
                    "WHERE session_id = ? ORDER BY created_at ASC",
                    (session_id,)
                )
                rows = await cursor.fetchall()
                await cursor.close()
                return [
                    {"role": role, "content": content}
                    for role, content in rows
                ]
        except Exception as e:
            logging.exception(
                f"Ошибка при получении сообщений для сессии {session_id}: {e}"
            )
            return []

    async def clear_session(self, session_id: int) -> None:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "DELETE FROM gpt_messages WHERE session_id = ?",
                    (session_id,)
                )
                await conn.commit()
        except Exception as e:
            logging.exception(
                f"Ошибка при очистке сессии {session_id}: {e}"
            )
