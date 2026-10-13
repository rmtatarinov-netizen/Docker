# my-flask-app

Простое Flask-приложение в контейнере Docker: три основных эндпоинта и проверка живости для `HEALTHCHECK`. Все ответы — только JSON.

- **Стек:** Flask 3.1.3, Python 3.12
- **Образ:** `python:3.12-slim`, непривилегированный пользователь `appuser` (uid 10001)
- **Порт:** 5000
- **Проверено на:** Docker 29.8.1, Docker Compose v5.5.1

## Требования

Docker с плагином Compose. Проверить версии:

```bash
docker --version
docker compose version
```

## Быстрый старт

```bash
docker compose up -d
docker compose ps
```

В колонке `STATUS` должно появиться `healthy` — это означает, что встроенная проверка `/healthz` прошла успешно.

Приложение доступно на <http://localhost:5000>.

Если образ уже существует, compose использует его как есть и пересборку не выполняет. После правки `app.py`, `requirements.txt` или `Dockerfile` заставьте compose пересобрать образ явно:

```bash
docker compose up -d --build
```

## Как это работает: пошагово

Ниже — путь от исходников до ответа приложения на порту 5000. Шаги 1–6 выполняются при сборке и запуске контейнера, шаг 7 описывает код, который обслуживает запросы.

### Шаг 1. Базовый образ

`FROM python:3.12-slim` (`Dockerfile:2`) — берём официальный облегчённый образ: Debian без лишних пакетов и Python 3.12. Точная версия Python важна, потому что от неё зависит поведение интерпретатора в контейнере.

### Шаг 2. Переменные окружения

`ENV ...` (`Dockerfile:5`) задаёт три переменные:

- `PYTHONDONTWRITEBYTECODE=1` — Python не создаёт `__pycache__` внутри контейнера;
- `PYTHONUNBUFFERED=1` — вывод не буферизуется, поэтому логи видны сразу, в том числе `docker compose logs -f`;
- `FLASK_APP=app` — Flask знает, что приложение лежит в `app.py`.

### Шаг 3. Установка зависимостей

`COPY requirements.txt .` и `RUN pip install --no-cache-dir -r requirements.txt` (`Dockerfile:10-11`) устанавливают Flask 3.1.3. `requirements.txt` копируется отдельно от кода намеренно: слой с зависимостями кэшируется и не пересобирается, пока не изменился сам файл зависимостей.

### Шаг 4. Безопасность: непривилегированный пользователь

`RUN useradd ... appuser` (`Dockerfile:14`) создаёт пользователя с UID 10001, `COPY --chown=appuser:appuser app.py .` (`Dockerfile:16`) копирует код сразу с нужными правами, а `USER appuser` (`Dockerfile:19`) переключает контейнер на этого пользователя. В результате процесс Flask работает без root-прав.

### Шаг 5. Порт и проверка живости

`EXPOSE 5000` (`Dockerfile:22`) объявляет порт, а `HEALTHCHECK` (`Dockerfile:25-26`) каждые 30 секунд запрашивает `http://127.0.0.1:5000/healthz`. Если три проверки подряд не проходят, Docker помечает контейнер как `unhealthy`.

### Шаг 6. Запуск

`CMD ["flask", "run", "--host", "0.0.0.0", "--port", "5000", "--no-reload"]` (`Dockerfile:29`) запускает встроенный dev-сервер Flask, слушающий все интерфейсы на порту 5000. Флаг `--no-reload` отключает автоперезагрузку — она не нужна в контейнере. `docker-compose.yml` дополняет это директивой `restart: unless-stopped`, поэтому контейнер поднимается заново после перезагрузки Docker.

### Шаг 7. Что делает код `app.py`

Приложение отвечает только JSON. Включение `app.json.ensure_ascii = False` (`app.py:9`) отключает экранирование, поэтому кириллица в текстах ошибок отдаётся читаемо.

| Маршрут | Где в коде | Что делает |
|---|---|---|
| `GET /` | `app.py:21` | Название сервиса, статус и карта маршрутов |
| `GET /info` | `app.py:35` | Версия Python, платформа, хост, PID, время работы (считается от `STARTED_AT`, `app.py:11`) |
| `GET /healthz` | `app.py:47` | Возвращает `{"status":"ok"}` для `HEALTHCHECK` |
| `GET /calc/<a>/<b>` | `app.py:52` | Арифметика: операция из `OPERATIONS` (`app.py:13`), по умолчанию `sum` |

В `/calc` операция берётся из параметра `op` и приводится к нижнему регистру (`app.py:54`); неизвестная операция и нечисловые аргументы возвращают JSON с кодом 400 (`app.py:55-70`), а деление на ноль отдельно проверяется при `op=div` (`app.py:72`). Для несуществующих путей срабатывает `@app.errorhandler(404)` (`app.py:78`), который также отвечает JSON-ошибкой вместо HTML-страницы.

## Запуск без compose

```bash
docker build -t my-flask-app .
docker run -d --name my-flask-app -p 5000:5000 my-flask-app
```

Флаг `--name` здесь обязателен. Без него Docker назначает контейнеру случайное имя наподобие `adoring_curle`, и обратиться к нему по имени `my-flask-app` не получится — `docker inspect` вернёт пустое значение вместо health-статуса.

**Важно:** не запускайте оба варианта одновременно. Оба публикуют порт 5000, поэтому второй упадёт с ошибкой `port is already allocated`. Если compose уже запущен, контейнер из `docker run` нужно сначала удалить:

```bash
docker rm -f my-flask-app
```

## Эндпоинты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/` | Название сервиса, статус и карта маршрутов |
| `GET` | `/info` | Версия Python, платформа, хост, PID, время работы |
| `GET` | `/healthz` | Проверка живости для `HEALTHCHECK` |
| `GET` | `/calc/<a>/<b>?op=sum\|diff\|prod\|div` | Арифметика над двумя числами, по умолчанию `op=sum` |

### Примеры

```bash
curl http://localhost:5000/
# {"endpoints":{...},"service":"my-flask-app","status":"ok"}

curl http://localhost:5000/info
# {"hostname":"67c2a891adf0","pid":1,"platform":"Linux-7.0.12-linuxkit-x86_64-with-glibc2.41",
#  "python":"3.12.14","service":"my-flask-app","uptime_seconds":5.271}

curl http://localhost:5000/healthz
# {"status":"ok"}

curl http://localhost:5000/calc/2/3
# {"a":2.0,"b":3.0,"op":"sum","result":5.0}

curl "http://localhost:5000/calc/7/2?op=div"
# {"a":7.0,"b":2.0,"op":"div","result":3.5}

curl "http://localhost:5000/calc/1e3/2?op=prod"
# {"a":1000.0,"b":2.0,"op":"prod","result":2000.0}
```

Операции: `sum` (сложение), `diff` (вычитание), `prod` (умножение), `div` (деление). Регистр не важен — `op=SUM` работает так же, как `op=sum`. Принимаются целые, дробные, отрицательные числа и экспоненциальная запись.

### Ошибочные ответы

Приложение не падает с трассировкой, а отвечает JSON-ошибкой с кодом 400:

```bash
curl "http://localhost:5000/calc/10/0?op=div"
# {"error":"деление на ноль"}

curl "http://localhost:5000/calc/2/3?op=abc"
# {"allowed":["diff","div","prod","sum"],"error":"неизвестная операция: abc"}

curl "http://localhost:5000/calc/x/2"
# {"error":"аргументы должны быть числами, получено a='x', b='2'"}

curl http://localhost:5000/nope
# {"error":"404: маршрут не найден"}
```

Обратите внимание: деление на ноль проверяется только при `op=div`. Запрос `/calc/1/0` без `op` — это обычное сложение, и он вернёт `{"result":1.0}`.

## Остановка и удаление

```bash
docker compose down
```

Удалить контейнер, запущенный вручную:

```bash
docker rm -f my-flask-app
```

Удалить образ:

```bash
docker rmi my-flask-app
```

## Логи и диагностика

```bash
docker compose logs -f
```

В логах видны все запросы; ответы 4xx выделяются цветом: 400 красным, 404 жёлтым.

Проверить состояние здоровья вручную:

```bash
docker inspect -f '{{.State.Health.Status}}' my-flask-app
# healthy
```

## Локальный запуск без Docker

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask run --host 0.0.0.0 --port 5000
```

Переменная `FLASK_APP=app` уже задана в `Dockerfile` для контейнера, а для локального запуска Flask найдёт `app.py` в текущем каталоге сам. Флаг `--host 0.0.0.0` нужен, чтобы приложение было доступно не только с `localhost`.

## Структура проекта

```
.
├── app.py               # приложение и все маршруты
├── requirements.txt     # зависимости: Flask==3.1.3
├── Dockerfile           # сборка образа, HEALTHCHECK, непривилегированный пользователь
├── docker-compose.yml   # запуск сервиса web на порту 5000
├── .dockerignore        # исключает __pycache__, .git, .venv, *.md из контекста сборки
└── README.md
```

## Ограничения и доработки

Приложение запущено на встроенном dev-сервере Flask (`flask run`). Он многопоточный, поэтому обычные запросы обслуживает корректно, но **не рассчитан на продакшен**: нет таймаутов, ограничений на количество клиентов и graceful-рестарта.

Для перехода на production-сервер gunicorn нужны две правки:

1. В `requirements.txt` добавить строку `gunicorn==26.2.0`.
2. В `Dockerfile` заменить `CMD` на:
   ```dockerfile
   CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app:app"]
   ```

После этого пересоберите образ: `docker build -t my-flask-app .`

Два места в `app.py`, которые стоит знать при доработке:

- Аргументы `/calc` разбираются через `float()` вручную, а не встроенным конвертером `<float:...>`. Регулярка `FloatConverter` требует вид `2.5` и отправила бы целые `/calc/2/3` в 404.
- Строка `app.json.ensure_ascii = False` отключает JSON-экранирование, иначе кириллица в тексте ошибок отдавалась бы как `\u0434\u0435\u043b...`.
