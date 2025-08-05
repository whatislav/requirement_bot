# Requirement Bot

A small Telegram bot built with **Python**, **aiogram** and **SQLite** that lets recruiters pick one of five vacancies, collects a résumé, and then responds on behalf of the employer. Each vacancy can only be taken once.

## Features

1. Inline menu with five buttons labelled `Вакансия 1-5`.
2. Once a vacancy is selected, it disappears for everyone else.
3. After a vacancy is chosen the bot:
   * Greets the user.
   * Sends a voice message linked to the vacancy.
   * Prompts the user to upload a résumé (as a document).
   * Sends the employer’s thank-you reply once the résumé arrives.

## Getting Started

### 1. Clone & Install

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Provide a Bot Token

Export your bot token as an environment variable or hard-code it in `bot.py`:

```bash
export BOT_TOKEN="123456:ABC-DEF…"
```

### 3. Add Voice Messages

Place your OGG/MP3 voice files inside the `voices/` directory:

```
voices/
 ├─ voice1.ogg
 ├─ voice2.ogg
 ├─ voice3.ogg
 ├─ voice4.ogg
 └─ voice5.ogg
```

> The file names **must** follow the pattern `voiceN.ogg`, where **N** is the vacancy number.

### 4. Run the Bot

```bash
python bot.py
```

The first start will create an SQLite database (`vacancies.db`) and pre-populate it with five vacancies.

## Project Structure

```
recquierement_bot/
├─ bot.py          # Main bot logic
├─ database.py     # SQLite helper functions
├─ requirements.txt
├─ README.md
└─ voices/         # Put your voice files here (not committed)
```

Enjoy!

## Docker

### Build the image

```bash
docker build -t requirement-bot .
```

### Run the container

```bash
docker run -e BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN" \
           -v "$PWD/voices:/app/voices" \
           -v "$PWD/vacancies.db:/app/vacancies.db" \
           requirement-bot
```

The command mounts your local `voices/` directory and the SQLite database file so that both persist across container restarts. Replace `YOUR_TELEGRAM_BOT_TOKEN` with your actual token before running.
 