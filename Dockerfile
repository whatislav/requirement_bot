# syntax=docker/dockerfile:1

# Use official Python runtime as the parent image
FROM python:3.11-slim

# Disable buffering so that Python logs are immediately flushed
ENV PYTHONUNBUFFERED=1

# Create and set the working directory
WORKDIR /app

# Install dependencies first (leverages Docker cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the application source code
COPY . .

# Default command to run the bot
CMD ["python", "bot.py"]