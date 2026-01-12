from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class Role:
    MANAGER = 'manager'
    SUPERVISOR = 'supervisor'
    EXECUTOR = 'executor'
    PRODUCTION_HEAD = 'production_head'
    DESIGN_HEAD = 'design_head'
    ADMIN = 'admin'
    CUSTOMER = 'customer'

    ALL = [MANAGER, SUPERVISOR, EXECUTOR, PRODUCTION_HEAD, DESIGN_HEAD, ADMIN, CUSTOMER]


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=Role.MANAGER)
    full_name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100))
    position = db.Column(db.String(100))
    phone = db.Column(db.String(20))

    # KPI и мотивация
    kpi_score = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    completed_tasks = db.Column(db.Integer, default=0)

    # Статус
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)

    # Связи
    created_requests = db.relationship('Request', backref='creator', lazy=True,
                                       foreign_keys='Request.manager_id')
    assigned_tasks = db.relationship('Task', backref='executor', lazy=True,
                                     foreign_keys='Task.executor_id')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, role):
        return self.role == role

    def can_create_request(self):
        return self.role in [Role.MANAGER, Role.SUPERVISOR, Role.ADMIN]

    def can_approve_request(self):
        return self.role in [Role.SUPERVISOR, Role.ADMIN]

    def update_kpi(self, points):
        """Обновление KPI пользователя"""
        self.kpi_score += points
        self.completed_tasks += 1
        self.rating = self.kpi_score / max(self.completed_tasks, 1)
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))