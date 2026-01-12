from django.core.mail import send_mail
from django.conf import settings
from ..models import Notification


def send_notification(user, request=None, message='', notification_type='info'):
    """Создание и отправка уведомления"""
    # Сохранение уведомления в БД
    notification = Notification.objects.create(
        user=user,
        request=request,
        message=message,
        notification_type=notification_type
    )

    # Отправка email если настроен
    if user.email and hasattr(settings, 'EMAIL_HOST') and settings.EMAIL_HOST:
        try:
            send_mail(
                'Уведомление от системы управления заявками',
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            # Логирование ошибки
            pass

    return True


def send_bulk_notification(users, message, notification_type='info'):
    """Массовая отправка уведомлений"""
    for user in users:
        send_notification(user, None, message, notification_type)
