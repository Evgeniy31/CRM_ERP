from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone


class Role(models.TextChoices):
    MANAGER = 'manager', 'Manager'
    SUPERVISOR = 'supervisor', 'Supervisor'
    EXECUTOR = 'executor', 'Executor'
    PRODUCTION_HEAD = 'production_head', 'Production Head'
    DESIGN_HEAD = 'design_head', 'Design Head'
    ADMIN = 'admin', 'Admin'
    CUSTOMER = 'customer', 'Customer'


class User(AbstractUser):
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.MANAGER)
    full_name = models.CharField(max_length=150)
    department = models.CharField(max_length=100, blank=True)
    position = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    # KPI и мотивация
    kpi_score = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    completed_tasks = models.IntegerField(default=0)

    # Статус
    is_verified = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.username} - {self.role}'

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
        self.save()


class RequestStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PENDING_VALIDATION = 'pending_validation', 'Pending Validation'
    VALIDATION_FAILED = 'validation_failed', 'Validation Failed'
    PENDING_APPROVAL = 'pending_approval', 'Pending Approval'
    APPROVED = 'approved', 'Approved'
    IN_PROGRESS = 'in_progress', 'In Progress'
    PENDING_MATERIALS = 'pending_materials', 'Pending Materials'
    COMPLETED = 'completed', 'Completed'
    SHIPPED = 'shipped', 'Shipped'
    CANCELLED = 'cancelled', 'Cancelled'


class RequestPriority(models.TextChoices):
    LOW = 'low', 'Low'
    MEDIUM = 'medium', 'Medium'
    HIGH = 'high', 'High'
    CRITICAL = 'critical', 'Critical'


class Request(models.Model):
    request_number = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Основные данные
    product_type = models.CharField(max_length=100)
    quantity = models.IntegerField(default=1)
    priority = models.CharField(max_length=20, choices=RequestPriority.choices, default=RequestPriority.MEDIUM)

    # Сроки
    requested_date = models.DateTimeField(default=timezone.now)
    deadline = models.DateTimeField(null=True, blank=True)
    estimated_completion = models.DateTimeField(null=True, blank=True)
    actual_completion = models.DateTimeField(null=True, blank=True)

    # Статус
    status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.DRAFT)
    completion_percentage = models.IntegerField(default=0)

    # Связи
    manager = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_requests')
    supervisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_requests')
    customer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_requests')

    # Файлы
    drawings_path = models.CharField(max_length=500, blank=True)
    specifications_path = models.CharField(max_length=500, blank=True)

    # Аналитика
    predicted_delay_days = models.IntegerField(default=0)
    risk_level = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.request_number} - {self.status}'

    def save(self, *args, **kwargs):
        if not self.request_number:
            self.request_number = self.generate_request_number()
        super().save(*args, **kwargs)

    def generate_request_number(self):
        """Генерация уникального номера заявки"""
        year = timezone.now().year
        prefix = 'REQ'
        last_request = Request.objects.order_by('-id').first()
        last_num = last_request.id if last_request else 0
        return f'{prefix}{year}{last_num + 1:06d}'

    def calculate_risk_level(self):
        """Расчет уровня риска задержки"""
        if not self.deadline:
            return None

        days_until_deadline = (self.deadline - timezone.now()).days

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
        tasks = self.tasks.all()
        if not tasks:
            self.completion_percentage = 0
            return

        completed_tasks = tasks.filter(status='completed').count()
        total_tasks = tasks.count()

        if total_tasks > 0:
            self.completion_percentage = int((completed_tasks / total_tasks) * 100)
        self.save()


class TaskStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    BLOCKED = 'blocked', 'Blocked'


class Task(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Исполнитель
    executor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    assigned_date = models.DateTimeField(null=True, blank=True)
    started_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)

    # Статус
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING)
    priority = models.CharField(max_length=20, default='medium')

    # Сроки
    estimated_hours = models.IntegerField(null=True, blank=True)
    actual_hours = models.IntegerField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.id} - {self.status}'


class Comment(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    is_internal = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.request.request_number}'


class Notification(models.Model):
    request = models.ForeignKey(Request, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=50, blank=True)
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Notification for {self.user.username}: {self.message[:50]}...'
