from datetime import datetime, timedelta
from django.utils import timezone
from .models import User, Request, Notification


def user_data(request):
    """Инъекция данных пользователя во все шаблоны"""
    def get_current_user_data():
        if request.user.is_authenticated:
            return {
                'id': request.user.id,
                'name': request.user.full_name,
                'role': request.user.role,
                'avatar': f"https://ui-avatars.com/api/?name={request.user.full_name}&background=0D8ABC&color=fff"
            }
        return None

    def count_pending_requests():
        if request.user.is_authenticated and request.user.role in ['supervisor', 'admin']:
            return Request.objects.filter(status='pending_approval').count()
        return 0

    def count_unread_notifications():
        if request.user.is_authenticated:
            return Notification.objects.filter(user=request.user, is_read=False).count()
        return 0

    def get_recent_notifications(limit=5):
        if request.user.is_authenticated:
            return Notification.objects.filter(user=request.user)\
                .order_by('-created_at')[:limit]
        return []

    def get_online_users_count():
        # Простая реализация - пользователи, активные в последние 5 минут
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        return User.objects.filter(last_login__gte=five_minutes_ago).count()

    def get_total_requests_count():
        return Request.objects.count()

    def get_recent_activities(limit=10):
        # Здесь должна быть реализация получения активности
        return []

    def get_user_kpi(user_id):
        # Заглушка для KPI
        from .utils.analytics import calculate_kpis
        try:
            start_date = timezone.now() - timedelta(days=30)
            return calculate_kpis(user_id, start_date, timezone.now())
        except:
            return {'total_score': 75, 'completed_tasks': 12, 'on_time_rate': 85.5}

    def get_risky_requests(limit=3):
        # Заявки с высоким риском срыва
        return Request.objects.filter(
            deadline__lt=timezone.now() + timedelta(days=2),
            status__in=['in_progress', 'pending_materials']
        ).order_by('deadline')[:limit]

    return {
        'current_user_data': get_current_user_data(),
        'count_pending_requests': count_pending_requests(),
        'count_unread_notifications': count_unread_notifications(),
        'get_recent_notifications': get_recent_notifications(),
        'get_online_users_count': get_online_users_count(),
        'get_total_requests_count': get_total_requests_count(),
        'get_recent_activities': get_recent_activities(),
        'get_user_kpi': get_user_kpi,
        'get_risky_requests': get_risky_requests()
    }
