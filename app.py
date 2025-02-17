import os
import requests
import bcrypt
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from dotenv import load_dotenv
from db import get_db, init_db, add_user, get_user_by_username, add_website, get_websites_by_user_id, add_check_result, get_website_by_id, get_checks_by_website_id, get_user_by_id
from urllib.parse import urlparse
from functools import wraps
import schedule
import time
import threading

# Загрузка переменных окружения из .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY')  # Считываем секретный ключ
if not app.secret_key:
    raise ValueError("FLASK_SECRET_KEY не установлен в .env файле!")


def check_website(url):
    """Проверяет доступность сайта по URL."""
    try:
        response = requests.get(url, timeout=5)  # Уменьшаем таймаут до 5 секунд
        response.raise_for_status()
        return {
            "url": url,  # добавили URL
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


# Декоратор для защиты роутов, требующих авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))  # Передаем URL, на который хотел попасть пользователь
        return f(*args, **kwargs)

    return decorated_function


@app.before_request
def before_request():
    """Выполняется перед каждым запросом."""
    g.user = None  # По умолчанию пользователь не авторизован
    if 'user_id' in session:
        user = get_user_by_id(session['user_id'])
        # ВАЖНО: Обработать случай, если пользователя нет в БД (например, удалили)
        if user:
            g.user = user  # Сохраняем информацию о пользователе в g
        else:
            # Если пользователя нет в БД, удаляем его из сессии
            session.pop('user_id', None)


@app.route("/")
def home():
    if g.user:  # Используем g.user
        return redirect(url_for('dashboard'))
    return render_template("index.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        # --- Добавляем валидацию ---
        if not username or not password or not email:
            flash("Все поля обязательны для заполнения")
            return render_template('register.html')
        if len(username) < 3 or len(username) > 20:  # Пример
            flash("Имя пользователя должно быть от 3 до 20 символов")
            return render_template('register.html')

        if len(password) < 6:  # Пример
            flash("Пароль должен быть не менее 6 символов")
            return render_template('register.html')
        # Добавь проверку формата email (можно с помощью регулярного выражения)
        # --- Конец валидации ---

        existing_user = get_user_by_username(username)
        if existing_user:
            flash("Пользователь с таким именем уже существует")
            return render_template('register.html')

        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        add_user(username, hashed_password, email)
        flash("Регистрация прошла успешно. Теперь войдите.")  # Добавляем flash
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
            next_url = request.args.get('next')  # получаем next
            return redirect(next_url or url_for('dashboard'))  # Перенаправляем на dashboard, или на next

        flash("Неверное имя пользователя или пароль")
        return render_template('login.html')  # Остаемся на странице login

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))


@app.route('/add_website', methods=['GET', 'POST'])
@login_required  # Используем декоратор
def add_website_route():
    if request.method == 'POST':
        url = request.form['url']
        user_id = session['user_id']  # user_id все еще доступен в сессии

        # --- Валидация URL ---
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):  # Проверяем наличие схемы и домена
                add_website(user_id, url)
                flash("Сайт успешно добавлен!")  # Добавляем flash-сообщение
                return redirect(url_for('dashboard'))  # Перенаправляем на dashboard
            else:
                flash("Неверный формат URL")
        except:
            flash("Неверный формат URL")
        return render_template('add_website.html')

    return render_template('add_website.html')


@app.route('/dashboard')
@login_required  # Используем декоратор
def dashboard():
    user = g.user
    username = user['username']
    websites = get_websites_by_user_id(user['id'])

    websites_with_checks = []
    for website in websites:
        last_check = get_checks_by_website_id(website['id'])
        if last_check:
            # Создаем новый словарь, объединяя данные
            combined_data = {
                **website,  # Разворачиваем словарь website
                'last_check': dict(last_check[0])  # Преобразуем last_check[0] в обычный словарь
            }
            websites_with_checks.append(combined_data)
        else:
              combined_data = {
                **website,
                'last_check': None  # Если проверок не было
            }
              websites_with_checks.append(combined_data)


    return render_template('dashboard.html', websites=websites_with_checks, username=username)



def check_and_save(website_id):
    """Проверяет сайт и сохраняет результат в БД."""
    website = get_website_by_id(website_id)
    if not website:
        print(f"Сайт с ID {website_id} не найден.")
        return

    result = check_website(website['url'])
    add_check_result(
        website_id,
        result['status'],
        result.get('response_time'),
        result.get('status_code'),
        result.get('error')
    )
    print(f"Проверен сайт {website['url']}, статус: {result['status']}")


def run_checks():
    """Запускает проверки для всех сайтов."""
    print("Запуск запланированных проверок...")
    with app.app_context():  # Нужен app_context для доступа к БД
        # получаем список всех сайтов, которые нужно проверить
        all_websites = []
        with get_db() as db:
            all_websites = db.execute("SELECT * FROM websites").fetchall()

        for website in all_websites:
            check_and_save(website['id'])


def run_schedule():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    # init_db()  # Убираем!

    # Планируем задачи
    schedule.every(10).seconds.do(run_checks)  # Запускать проверки каждые 10 секунд

    # Запускаем schedule в отдельном потоке
    schedule_thread = threading.Thread(target=run_schedule)
    schedule_thread.daemon = True  # Чтобы поток завершился при выходе из приложения
    schedule_thread.start()

    app.run(debug=True, host='0.0.0.0')  # Запускаем Flask