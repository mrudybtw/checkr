import os
import requests
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from db import get_db, init_db, add_user, get_user_by_username, add_website, get_websites_by_user_id, add_check_result, get_website_by_id, get_checks_by_website_id

# Загрузка переменных окружения из .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')  # Считываем секретный ключ
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY не установлен в .env файле!")

def check_website(url):
    """Проверяет доступность сайта по URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return {
            "url": url, #добавили URL
            "status": "available",
            "response_time": response.elapsed.total_seconds() * 1000,
            "status_code": response.status_code,
        }
    except requests.exceptions.RequestException as e:
        return {
            "url": url,
            "status": "unavailable",
            "error": str(e),
            "status_code": None,
        }

@app.r