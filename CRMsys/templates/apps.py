from datetime import datetime, timedelta
from flask import session
from models.user import User
from models.request import Request, Notification
from functools import wraps

@app.context_processor
def inject_user_data():
    """Инъекция данных пользователя во все шаблоны"""
    def get_current_user_data():
        if hasattr(current_user, 'id'):
            return {
                'id': current_user.id,
                'name': current_user.full_name,
                'role': current_user.role,
                'avatar': f"https://ui-avatars.com/api/?name={current_user.full_name}&background=0D8ABC&color=fff"
            }
        return None
    
    def count_pending_requests():
        if current_user.is_authenticated and current_user.role in ['supervisor', 'admin']:
            return Request.query.filter_by(status='pending_approval').count()
        return 0
    
    def count_unread_notifications():
        if current_user.is_authenticated:
            return Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return 0
    
    def get_recent_notifications(limit=5):
        if current_user.is_authenticated:
            return Notification.query.filter_by(user_id=current_user.id)\
                .order_by(Notification.created_at.desc())\
                .limit(limit).all()
        return []
    
    def get_online_users_count():
        # Простая реализация - пользователи, активные в последние 5 минут
        five_minutes_ago = datetime.utcnow() - timedelta(minutes=5)
        return User.query.filter(User.last_login >= five_minutes_ago).count()
    
    def get_total_requests_count():
        return Request.query.count()
    
    def get_recent_activities(limit=10):
        # Здесь должна быть реализация получения активности
        return []
    
    def get_user_kpi(user_id):
        # Заглушка для KPI
        from utils.analytics import calculate_kpis
        try:
            start_date = datetime.utcnow() - timedelta(days=30)
            return calculate_kpis(user_id, start_date, datetime.utcnow())
        except:
            return {'total_score': 75, 'completed_tasks': 12, 'on_time_rate': 85.5}
    
    def get_risky_requests(limit=3):
        # Заявки с высоким риском срыва
        return Request.query.filter(
            Request.deadline < datetime.utcnow() + timedelta(days=2),
            Request.status.in_(['in_progress', 'pending_materials'])
        ).order_by(Request.deadline.asc()).limit(limit).all()
    
    return dict(
        current_user_data=get_current_user_data,
        count_pending_requests=count_pending_requests,
        count_unread_notifications=count_unread_notifications,
        get_recent_notifications=get_recent_notifications,
        get_online_users_count=get_online_users_count,
        get_total_requests_count=get_total_requests_count,
        get_recent_activities=get_recent_activities,
        get_user_kpi=get_user_kpi,
        get_risky_requests=get_risky_requests
    )

# Фильтр для форматирования времени
@app.template_filter('timesince')
def timesince_filter(dt):
    """Фильтр для отображения времени в формате "сколько времени назад" """
    now = datetime.utcnow()
    diff = now - dt
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} год{'а' if years % 10 in [2,3,4] and years % 100 not in [12,13,14] else '' if years % 10 == 1 and years % 100 != 11 else 'ов'} назад"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} месяц{'а' if months % 10 in [2,3,4] and months % 100 not in [12,13,14] else '' if months % 10 == 1 and months % 100 != 11 else 'ев'} назад"
    elif diff.days > 0:
        return f"{diff.days} д{'ень' if diff.days % 10 == 1 and diff.days % 100 != 11 else 'ня' if diff.days % 10 in [2,3,4] and diff.days % 100 not in [12,13,14] else 'ней'} назад"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} час{'а' if hours % 10 in [2,3,4] and hours % 100 not in [12,13,14] else '' if hours % 10 == 1 and hours % 100 != 11 else 'ов'} назад"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} минут{'ы' if minutes % 10 in [2,3,4] and minutes % 100 not in [12,13,14] else '' if minutes % 10 == 1 and minutes % 100 != 11 else ''} назад"
    else:
        return "только что"