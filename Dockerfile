# Базовий образ Python
FROM python:3.12-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо бібліотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо весь код
COPY . .

# Команда для запуску
CMD ["python", "main.py"]
