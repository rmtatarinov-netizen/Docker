import os
import platform
import socket
import time

from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.ensure_ascii = False

STARTED_AT = time.time()

OPERATIONS = {
    "sum": lambda a, b: a + b,
    "diff": lambda a, b: a - b,
    "prod": lambda a, b: a * b,
    "div": lambda a, b: a / b,
}


@app.get("/")
def index():
    return jsonify(
        service="my-flask-app",
        status="ok",
        endpoints={
            "/": "этот же ответ",
            "/info": "сведения об окружении контейнера",
            "/calc/<a>/<b>?op=sum|diff|prod|div": "арифметика над двумя числами, по умолчанию op=sum",
            "/healthz": "проверка живости для HEALTHCHECK",
        },
    )


@app.get("/info")
def info():
    return jsonify(
        service="my-flask-app",
        python=platform.python_version(),
        platform=platform.platform(),
        hostname=socket.gethostname(),
        pid=os.getpid(),
        uptime_seconds=round(time.time() - STARTED_AT, 3),
    )


@app.get("/healthz")
def healthz():
    return jsonify(status="ok")


@app.get("/calc/<a>/<b>")
def calc(a, b):
    op = request.args.get("op", "sum").lower()
    if op not in OPERATIONS:
        return (
            jsonify(
                error=f"неизвестная операция: {op}",
                allowed=sorted(OPERATIONS),
            ),
            400,
        )

    try:
        x, y = float(a), float(b)
    except ValueError:
        return (
            jsonify(error=f"аргументы должны быть числами, получено a={a!r}, b={b!r}"),
            400,
        )

    if op == "div" and y == 0:
        return jsonify(error="деление на ноль"), 400

    return jsonify(a=x, b=y, op=op, result=OPERATIONS[op](x, y))


@app.errorhandler(404)
def not_found(_):
    return jsonify(error="404: маршрут не найден"), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
