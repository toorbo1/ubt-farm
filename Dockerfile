FROM python:3.11-slim

# Установить FFmpeg для видео
RUN apt-get update && \
    apt-get install -y ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копировать зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копировать проект
COPY . .

# Создать директории для вывода
RUN mkdir -p output/scenes assets/backgrounds profiles logs

# Запуск бота
CMD ["python", "bot/run_bot.py", "--bot", "1"]
