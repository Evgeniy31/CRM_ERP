from datetime import datetime, timedelta
from app import db


class RequestStatus:
    DRAFT = 'draft'
    PENDING_VALIDATION = 'pending_validation'
    VALIDATION_FAILED = 'validation_failed'
    PENDING_APPROVAL = 'pending_approval'
    APPROVED = 'approved'
    IN_PROGRESS = 'in_progress'
    PENDING_MATERIALS = 'pending_materials'
    COMPLETED = 'completed'
    SHIPPED = 'shipped'
    CANCELLED = 'cancelled'

    ALL = [DRAFT, PENDING_VALIDATION, VALIDATION_FAILED, PENDING_APPROVAL,
           APPROVED, IN_PROGRESS, PENDING_MATERIALS, COMPLETED, SHIPPED, CANCELLED]


class RequestPriority:
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'

    ALL = [LOW, MEDIUM, HIGH, CRITICAL]


class Request(db.Model):
    __tablename__ = 'requests'

    id = db.Column(db.Integer, primary_key=True)
    request_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Основные данные
    product_type = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    priority = db.Column(db.String(20), default=RequestPriority.MEDIUM)

    # Сроки
    requested_date = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime)
    estimated_completion = db.Column(db.DateTime)
    actual_completion = db.Column(db.DateTime)

    # Статус
    status = db.Column(db.String(30), default=RequestStatus.DRAFT)
    completion_percentage = db.Column(db.Integer, default=0)

    # Связи
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    supervisor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Файлы
    drawings_path = db.Column(db.String(500))
    specifications_path = db.Column(db.String(500))

    # Аналитика
    predicted_delay_days = db.Column(db.Integer, default=0)
    risk_level = db.Column(db.String(20))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    tasks = db.relationship('Task', backref='request', lazy=True, cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='request', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='request', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Request {self.request_number} - {self.status}>'

    def generate_request_number(self):
        """Генерация уникального номера заявки"""
        year = datetime.utcnow().year
        prefix = 'REQ'
        last_request = Request.query.order_by(Request.id.desc()).first()
        last_num = last_request.id if last_request else 0
        return f'{prefix}{year}{last_num + 1:06d}'

    def calculate_risk_level(self):
        """Расчет уровня риска задержки"""
        if not self.deadline:
            return None

        days_until_deadline = (self.deadline - datetime.utcnow()).days

        if days_until_deadline < 0:
            return 'critical'
        elif days_until_deadline <= 2:
            return 'high'
        elif days_until_deadline <= 5:
            return 'medium'
        else:
            return 'low'

    def update_completion_percentage(self):
        """Обновление процента готовности на основе задач"""
        if not self.tasks:
            self.completion_percentage = 0
            return

        completed_tasks = sum(1 for task in self.tasks if task.status == 'completed')
        total_tasks = len(self.tasks)

        if total_tasks > 0:
            self.completion_percentage = int((completed_tasks / total_tasks) * 100)

        db.session.commit()


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Исполнитель
    executor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_date = db.Column(db.DateTime)
    started_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)

    # Статус
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, blocked
    priority = db.Column(db.String(20), default='medium')

    # Сроки
    estimated_hours = db.Column(db.Integer)
    actual_hours = db.Column(db.Integer)
    deadline = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.id} - {self.status}>'


class Comment(db.Model):
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='comments')


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('requests.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))
    is_read = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')