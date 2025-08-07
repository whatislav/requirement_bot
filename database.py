import aiosqlite

DB_PATH = "vacancies.db"


async def init_db():
    """Initialize the database and pre-populate 5 vacancies if they are missing."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS vacancies (
                id INTEGER PRIMARY KEY,
                title TEXT,
                voice_path TEXT,
                taken INTEGER DEFAULT 0
            )
            """
        )
        # Insert default vacancies if they are not present
        for i in range(1, 5):
            cursor = await db.execute("SELECT 1 FROM vacancies WHERE id = ?", (i,))
            row = await cursor.fetchone()
            if not row:
                await db.execute(
                    "INSERT INTO vacancies (id, title, voice_path, taken) VALUES (?, ?, ?, 0)",
                    (
                        i,
                        f"Вакансия {i}",
                        f"voices/voice{i}.ogg",
                    ),
                )
        await db.commit()


async def get_available():
    """Return a list of (id, title) tuples for vacancies that are still available."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, title FROM vacancies")
        return await cursor.fetchall()


async def take_vacancy(vac_id: int):
    """Mark a vacancy as taken; return (id, title, voice_path) if successful, else None."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT taken FROM vacancies WHERE id = ?", (vac_id,))
        row = await cursor.fetchone()

        await db.execute("UPDATE vacancies SET taken = 1 WHERE id = ?", (vac_id,))
        cursor = await db.execute(
            "SELECT id, title, voice_path FROM vacancies WHERE id = ?", (vac_id,)
        )
        info = await cursor.fetchone()
        await db.commit()
        return info


async def get_voice_path(vac_id: int):
    """Convenience helper to fetch the stored voice file path for a vacancy."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT voice_path FROM vacancies WHERE id = ?", (vac_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def update_voice_path(vac_id: int, new_ref: str):
    """Update the stored voice reference (file path or Telegram file_id)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE vacancies SET voice_path = ? WHERE id = ?", (new_ref, vac_id))
        await db.commit()


async def reset_vacancies():
    """Reset all vacancies to available (taken = 0)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE vacancies SET taken = 0")
        await db.commit()
 