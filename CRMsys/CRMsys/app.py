import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery
from config import Config

# Инициализация расширений
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Настройка логина
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'warning'

    # Инициализация расширений
    db.init_app(app)
    migrate.init_app(app, db)
    celery.conf.update(app.config)

    # Регистрация Blueprints
    from routes.auth import auth_bp
    from routes.requests import requests_bp
    from routes.admin import admin_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(requests_bp, url_prefix='/requests')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Главная страница
    @app.route('/')
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Дашборд системы"""
        user = current_user

        if user.role == 'manager':
            # Дашборд менеджера
            requests = Request.query.filter_by(manager_id=user.id).order_by(Request.created_at.desc()).limit(10).all()
            stats = {
                'total': Request.query.filter_by(manager_id=user.id).count(),
                'in_progress': Request.query.filter_by(manager_id=user.id, status='in_progress').count(),
                'completed': Request.query.filter_by(manager_id=user.id, status='completed').count(),
                'pending': Request.query.filter_by(manager_id=user.id, status='pending_approval').count()
            }

        elif user.role == 'supervisor':
            # Дашборд руководителя
            requests = Request.query.filter_by(supervisor_id=user.id).order_by(Request.created_at.desc()).limit(
                10).all()
            stats = {
                'total': Request.query.filter_by(supervisor_id=user.id).count(),
                'awaiting_approval': Request.query.filter_by(status='pending_approval').count(),
                'high_priority': Request.query.filter_by(priority='high').count(),
                'delayed': Request.query.filter("deadline < CURRENT_DATE AND status != 'completed'").count()
            }

        elif user.role == 'executor':
            # Дашборд исполнителя
            tasks = Task.query.filter_by(executor_id=user.id).order_by(Task.deadline.asc()).limit(10).all()
            stats = {
                'total_tasks': Task.query.filter_by(executor_id=user.id).count(),
                'in_progress': Task.query.filter_by(executor_id=user.id, status='in_progress').count(),
                'completed': Task.query.filter_by(executor_id=user.id, status='completed').count(),
                'overdue': Task.query.filter(
                    Task.executor_id == user.id,
                    Task.deadline < datetime.utcnow(),
                    Task.status != 'completed'
                ).count()
            }
            return render_template('executor_dashboard.html', tasks=tasks, stats=stats, user=user)

        elif user.role == 'production_head':
            # Дашборд начальника производства
            requests = Request.query.filter_by(status='in_progress').order_by(Request.priority.desc()).limit(10).all()
            stats = {
                'total_in_progress': Request.query.filter_by(status='in_progress').count(),
                'pending_materials': Request.query.filter_by(status='pending_materials').count(),
                'completion_avg': db.session.query(db.func.avg(Request.completion_percentage)).scalar() or 0,
                'delayed': Request.query.filter("deadline < CURRENT_DATE AND status != 'completed'").count()
            }

        elif user.role == 'admin':
            return redirect(url_for('admin.dashboard'))

        else:
            flash('У вас нет доступа к дашборду', 'error')
            return redirect(url_for('auth.login'))

        return render_template('dashboard.html',
                               requests=requests,
                               stats=stats,
                               user=user,
                               now=datetime.utcnow())

    @app.route('/profile')
    @login_required
    def profile():
        """Страница профиля пользователя"""
        return render_template('profile.html', user=current_user)

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    # Команды CLI для управления
    @app.cli.command('create-admin')
    def create_admin():
        """Создание администратора"""
        from models.user import User
        from getpass import getpass

        email = input('Email: ')
        username = input('Username: ')
        full_name = input('Full name: ')
        password = getpass('Password: ')
        confirm = getpass('Confirm password: ')

        if password != confirm:
            print('Пароли не совпадают!')
            return

        admin = User(
            email=email,
            username=username,
            full_name=full_name,
            role='admin'
        )
        admin.password = password

        try:
            db.session.add(admin)
            db.session.commit()
            print(f'Администратор {username} создан успешно!')
        except Exception as e:
            db.session.rollback()
            print(f'Ошибка: {e}')

    @app.cli.command('seed-data')
    def seed_data():
        """Наполнение базы тестовыми данными"""
        from models.user import User, Role

        # Создание тестовых пользователей
        users_data = [
            {'email': 'manager@company.com', 'username': 'manager1', 'full_name': 'Иванов Иван', 'role': Role.MANAGER,
             'password': 'manager123'},
            {'email': 'supervisor@company.com', 'username': 'supervisor1', 'full_name': 'Петров Петр',
             'role': Role.SUPERVISOR, 'password': 'supervisor123'},
            {'email': 'executor@company.com', 'username': 'executor1', 'full_name': 'Сидоров Сидор',
             'role': Role.EXECUTOR, 'password': 'executor123'},
            {'email': 'production@company.com', 'username': 'prodhead1', 'full_name': 'Кузнецов Алексей',
             'role': Role.PRODUCTION_HEAD, 'password': 'production123'},
            {'email': 'design@company.com', 'username': 'designhead1', 'full_name': 'Орлова Мария',
             'role': Role.DESIGN_HEAD, 'password': 'design123'},
        ]

        for user_data in users_data:
            if not User.query.filter_by(email=user_data['email']).first():
                user = User(
                    email=user_data['email'],
                    username=user_data['username'],
                    full_name=user_data['full_name'],
                    role=user_data['role']
                )
                user.password = user_data['password']
                db.session.add(user)

        db.session.commit()
        print('Тестовые данные созданы успешно!')

    return app


# Инициализация приложения
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)