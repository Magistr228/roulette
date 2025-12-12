from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    balance = db.Column(db.Integer, default=1000)
    achievement_unlocked = db.Column(db.Boolean, default=False)
    total_bets = db.Column(db.Integer, default=0)
    total_wins = db.Column(db.Integer, default=0)
    total_win_amount = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

    bets = db.relationship('Bet', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'


class Bet(db.Model):
    __tablename__ = 'bets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    bet_type = db.Column(db.String(20), nullable=False)  # 'red', 'black', 'number'
    bet_value = db.Column(db.Integer, nullable=True)  # Для числа
    amount = db.Column(db.Integer, nullable=False)
    result = db.Column(db.String(20))  # 'win', 'lose'
    win_amount = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Bet {self.id} by User {self.user_id}>'


def init_db(app):
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        print("Database tables created successfully")

        # Создаем админа если его нет
        from werkzeug.security import generate_password_hash
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                balance=10000,
                is_admin=True,
                total_bets=0,
                total_wins=0,
                total_win_amount=0,
                achievement_unlocked=False
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin / admin123")

        print("\nDatabase initialized successfully!")