import os
import requests
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv
from db import get_db, add_user, get_user_by_username, add_website, get_websites_by_user_id, add_check_result, get_website_by_id, get_checks_by_website_id

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
            "status": "available",
            "response_time": response.elapsed.total_seconds() * 1000,
            "status_code": response.status_code,
        }
    except requests.exceptions.RequestException as e:
        return {
            "status": "unavailable",
            "error": str(e),
            "status_code": None,
        }

@app.route("/")
def home():
    if 'user_id' in session:
        user_id = session['user_id']
        websites = get_websites_by_user_id(user_id)
        return render_template("dashboard.html", websites=websites)
    return render_template("index.html")

@app.route("/check", methods=["GET"])
def check():
    url = request.args.get("url")
    if not url:
        return "Необходимо указать URL", 400

    result = check_website(url)

    # Сохраняем в базу (пример - нужно доработать логику получения website_id)
    if 'user_id' in session:
        # Временно берем первый сайт пользователя.  TODO:  Сделать выбор сайта.
        websites = get_websites_by_user_id(session['user_id'])
        if websites:
             website_id = websites[0]['id']  # Первый сайт пользователя
             add_check_result(website_id, result['status'], result.get('response_time'), result.get('status_code'), result.get('error'))

    return render_template("check_result.html", result=result)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        existing_user = get_user_by_username(username)
        if existing_user:
            return "Пользователь с таким именем уже существует", 400

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        add_user(username, hashed_password, email)
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = get_user_by_username(username)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            return redirect(url_for('home'))

        return "Неверное имя пользователя или пароль", 401

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/add_website', methods=['GET', 'POST'])
def add_website_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        url = request.form['url']
        user_id = session['user_id']
        add_website(user_id, url)
        return redirect(url_for('home'))

    return render_template('add_website.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    websites = get_websites_by_user_id(user_id)

    websites_with_checks = []
    for website in websites:
        last_check = get_checks_by_website_id(website['id'])
        if last_check:
            website['last_check'] = last_check[0]
        websites_with_checks.append(website)
    return render_template('dashboard.html', websites=websites_with_checks)

if __name__ == "__main__":
    app.run(debug=False)  # debug=False для production!