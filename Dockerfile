# Базовый образ: облегчённый Python 3.12
FROM python:3.12-slim

# Переменные окружения: без .pyc, без буферизации вывода, FLASK_APP=app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app

# Рабочая директория внутри контейнера
WORKDIR /app

# Копируем зависимости и устанавливаем их без кэша
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Создаём непривилегированного пользователя (UID 10001)
RUN useradd --create-home --uid 10001 appuser
# Копируем код приложения с правами appuser
COPY --chown=appuser:appuser app.py .

# Запуск от непривилегированного пользователя
USER appuser

# Открываем порт 5000
EXPOSE 5000

# Проверка здоровья: запрос к /healthz каждые 30 с
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz', timeout=2).read()"

# Запуск Flask на 0.0.0.0:5000 без авто-перезагрузки
CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000", "--no-reload"]
