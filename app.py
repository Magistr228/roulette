from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import random
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

from config import Config
from database import db, User, Bet, init_db
from forms import LoginForm, RegisterForm

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация расширений
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        # Хешируем пароль
        hashed_password = generate_password_hash('admin123')
        admin = User(
            username='admin',
            password_hash=hashed_password,
            balance=10000,
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Администратор создан: admin / admin123")


# Главная страница
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('game'))
    return render_template('index.html')


# Страница игры
@app.route('/game')
@login_required
def game():
    return render_template('game.html', user=current_user)


# Страница профиля
@app.route('/profile')
@login_required
def profile():
    user_stats = {
        'total_bets': current_user.total_bets or 0,
        'total_wins': current_user.total_wins or 0,
        'total_win_amount': current_user.total_win_amount or 0,
        'win_rate': round((current_user.total_wins / current_user.total_bets * 100),
                          2) if current_user.total_bets and current_user.total_bets > 0 else 0
    }
    return render_template('profile.html', user=current_user, stats=user_stats)


# Админ панель
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('У вас нет прав администратора!', 'danger')
        return redirect(url_for('game'))

    users = User.query.all()

    # Собираем статистику для админ-панели
    stats = {
        'total_users': len(users),
        'total_balance': sum(user.balance or 0 for user in users),
        'total_bets': sum(user.total_bets or 0 for user in users),
        'active_today': len([u for u in users if
                             u.bets and any(bet.created_at.date() == datetime.utcnow().date() for bet in u.bets[:5])])
    }

    return render_template('admin.html', users=users, stats=stats)


# Админ: управление балансом
@app.route('/admin/balance', methods=['POST'])
@login_required
def admin_balance():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})

    try:
        data = request.json
        user_id = data.get('user_id')
        amount = int(data.get('amount', 0))

        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Пользователь не найден'})

        if user.balance is None:
            user.balance = 0

        user.balance += amount
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Баланс пользователя {user.username} изменен',
            'new_balance': user.balance,
            'username': user.username
        })
    except Exception as e:
        print(f"Error in admin_balance: {e}")
        return jsonify({'success': False, 'message': 'Произошла ошибка'})


# Админ: отправка сообщения
@app.route('/admin/message', methods=['POST'])
@login_required
def admin_message():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Доступ запрещен'})

    try:
        data = request.json
        user_id = data.get('user_id')
        message = data.get('message')
        message_type = data.get('type', 'info')

        if not message or not user_id:
            return jsonify({'success': False, 'message': 'Не указаны данные'})

        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Пользователь не найден'})

        # Здесь должен быть код отправки сообщения
        # В реальном приложении можно сохранять в БД или отправлять через email/telegram

        # Для демо просто логируем
        print(f"Сообщение для {user.username} ({user_id}): {message}")

        return jsonify({
            'success': True,
            'message': f'Сообщение отправлено пользователю {user.username}'
        })
    except Exception as e:
        print(f"Error in admin_message: {e}")
        return jsonify({'success': False, 'message': 'Произошла ошибка'})


# API для ставок
@app.route('/api/bet', methods=['POST'])
@login_required
def place_bet():
    try:
        data = request.json
        bet_type = data.get('type')
        amount = int(data.get('amount', 0))
        number = data.get('number')

        # Проверка баланса
        if amount > current_user.balance:
            return jsonify({'success': False, 'message': 'Недостаточно средств!'})

        if amount <= 0:
            return jsonify({'success': False, 'message': 'Сумма ставки должна быть положительной!'})

        if amount < 10:
            return jsonify({'success': False, 'message': 'Минимальная ставка: 10!'})

        # Для ставки на число
        if bet_type == 'number' and number:
            number = int(number)
            if number < 0 or number > 36:
                return jsonify({'success': False, 'message': 'Число должно быть от 0 до 36'})

        # Списываем средства
        current_user.balance -= amount

        # Инициализируем счетчики, если они None
        if current_user.total_bets is None:
            current_user.total_bets = 0
        if current_user.total_wins is None:
            current_user.total_wins = 0
        if current_user.total_win_amount is None:
            current_user.total_win_amount = 0

        current_user.total_bets += 1

        # Крутим рулетку
        winning_number = random.randint(0, 36)
        winning_color = 'green' if winning_number == 0 else 'red' if winning_number % 2 == 1 else 'black'

        win = False
        win_amount = 0

        if bet_type == 'red':
            if winning_color == 'red':
                win = True
                win_amount = amount * 2
        elif bet_type == 'black':
            if winning_color == 'black':
                win = True
                win_amount = amount * 2
        elif bet_type == 'number':
            if winning_number == number:
                win = True
                win_amount = amount * 36

        # Записываем результат
        if win:
            current_user.balance += win_amount
            current_user.total_wins += 1
            current_user.total_win_amount += win_amount
            result = 'win'
        else:
            result = 'lose'

        # Сохраняем ставку в историю
        bet = Bet(
            user_id=current_user.id,
            bet_type=bet_type,
            bet_value=number if bet_type == 'number' else None,
            amount=amount,
            result=result,
            win_amount=win_amount if win else 0
        )

        # Проверяем достижение
        if current_user.balance >= 3000 and not current_user.achievement_unlocked:
            current_user.achievement_unlocked = True

        db.session.add(bet)
        db.session.commit()

        return jsonify({
            'success': True,
            'win': win,
            'winning_number': winning_number,
            'winning_color': winning_color,
            'win_amount': win_amount,
            'new_balance': current_user.balance,
            'achievement_unlocked': current_user.achievement_unlocked and win
        })
    except Exception as e:
        print(f"Error in place_bet: {e}")
        return jsonify({'success': False, 'message': 'Произошла ошибка'})


# История ставок
@app.route('/api/bets/history')
@login_required
def get_bet_history():
    bets = Bet.query.filter_by(user_id=current_user.id) \
        .order_by(Bet.created_at.desc()) \
        .limit(10).all()

    history = []
    for bet in bets:
        history.append({
            'id': bet.id,
            'type': bet.bet_type,
            'number': bet.bet_value,
            'amount': bet.amount,
            'result': bet.result,
            'win_amount': bet.win_amount,
            'created_at': bet.created_at.strftime('%H:%M %d.%m') if bet.created_at else 'Неизвестно'
        })

    return jsonify({'bets': history})


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('game'))

    form = RegisterForm()
    if form.validate_on_submit():
        # Проверяем, существует ли пользователь
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Пользователь с таким именем уже существует!', 'danger')
            return redirect(url_for('register'))

        # Хешируем пароль
        hashed_password = generate_password_hash(form.password.data)

        # Создаем нового пользователя
        user = User(
            username=form.username.data,
            password_hash=hashed_password,
            balance=1000,
            total_bets=0,
            total_wins=0,
            total_win_amount=0,
            achievement_unlocked=False
        )
        db.session.add(user)
        db.session.commit()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('game'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Вы успешно вошли в систему!', 'success')
            return redirect(url_for('game'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')

    return render_template('login.html', form=form)


# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


if __name__ == '__main__':
    init_db(app)
    app.run(debug=True, port=5000)