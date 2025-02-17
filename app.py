import requests
from flask import Flask, render_template, request

app = Flask(__name__)

def check_website(url):
    """Проверяет доступность сайта по URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Вызывает исключение для кодов 4xx и 5xx
        return {
            "status": "available",
            "response_time": response.elapsed.total_seconds() * 1000,  # Время в мс
            "status_code": response.status_code,
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "unavailable",
            "error": str(e),
            "status_code": None,  # Код статуса может отсутствовать при ошибке
        }

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/check", methods=["GET"])
def check():
    url = request.args.get("url")
    if not url:
        return "Необходимо указать URL", 400

    result = check_website(url)
    return render_template("check_result.html", result=result)

if __name__ == "__main__":
    app.run(debug=True)  # Удали debug=True при деплое на сервер!