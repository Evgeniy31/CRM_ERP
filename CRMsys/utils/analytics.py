import numpy as np
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import Request, RequestStatus


def predict_completion_date(product_type, priority, quantity):
    """Прогнозирование даты завершения заявки"""
    # Получение исторических данных
    historical_data = Request.query.filter_by(
        product_type=product_type,
        status=RequestStatus.COMPLETED
    ).all()

    if not historical_data:
        # Если нет исторических данных, используем эвристику
        base_days = {
            'low': 14,
            'medium': 10,
            'high': 7,
            'critical': 3
        }

        days = base_days.get(priority, 10)
        days += max(0, (quantity - 1) * 0.5)  # Учет количества

        return datetime.utcnow() + timedelta(days=days)

    # Анализ исторических данных
    lead_times = []
    quantities = []

    for request in historical_data:
        if request.actual_completion and request.requested_date:
            lead_time = (request.actual_completion - request.requested_date).days
            lead_times.append(lead_time)
            quantities.append(request.quantity)

    if len(lead_times) < 3:
        # Недостаточно данных для регрессии
        avg_lead_time = np.mean(lead_times) if lead_times else 10
        estimated_days = avg_lead_time * (quantity / (np.mean(quantities) if quantities else 1))
    else:
        # Использование линейной регрессии
        X = np.array(quantities).reshape(-1, 1)
        y = np.array(lead_times)

        model = LinearRegression()
        model.fit(X, y)
        estimated_days = model.predict([[quantity]])[0]

    # Корректировка на приоритет
    priority_multiplier = {
        'low': 1.2,
        'medium': 1.0,
        'high': 0.8,
        'critical': 0.6
    }

    estimated_days *= priority_multiplier.get(priority, 1.0)

    return datetime.utcnow() + timedelta(days=max(1, int(estimated_days)))


def calculate_kpis(user_id, start_date, end_date):
    """Расчет KPI для пользователя"""
    from ..models import User, Task

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return {
            'completed_tasks': 0,
            'avg_completion_time': 0,
            'on_time_rate': 0,
            'quality_score': 0,
            'total_score': 0
        }

    # Задачи пользователя за период
    tasks = Task.objects.filter(
        executor_id=user_id,
        completed_date__gte=start_date,
        completed_date__lte=end_date
    )

    if not tasks.exists():
        return {
            'completed_tasks': 0,
            'avg_completion_time': 0,
            'on_time_rate': 0,
            'quality_score': 0,
            'total_score': 0
        }

    # Метрики
    completed_tasks = tasks.count()
    total_completion_time = 0
    on_time_count = 0
    quality_score_sum = 0

    for task in tasks:
        if task.started_date and task.completed_date:
            completion_time = (task.completed_date - task.started_date).total_seconds() / 3600
            total_completion_time += completion_time

            # Проверка соблюдения сроков
            if task.deadline and task.completed_date <= task.deadline:
                on_time_count += 1

        # Оценка качества (можно добавить систему оценки)
        quality_score_sum += 1.0  # Заглушка

    avg_completion_time = total_completion_time / completed_tasks if completed_tasks > 0 else 0
    on_time_rate = (on_time_count / completed_tasks) * 100 if completed_tasks > 0 else 0
    avg_quality_score = quality_score_sum / completed_tasks if completed_tasks > 0 else 0

    # Итоговый балл KPI
    total_score = (
                          (completed_tasks * 10) +
                          (100 - min(avg_completion_time, 100)) +
                          on_time_rate +
                          (avg_quality_score * 100)
                  ) / 4

    return {
        'completed_tasks': completed_tasks,
        'avg_completion_time': avg_completion_time,
        'on_time_rate': on_time_rate,
        'quality_score': avg_quality_score,
        'total_score': total_score
    }


def generate_production_report(start_date, end_date):
    """Генерация отчета по производству"""
    # Заявки за период
    requests = Request.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )

    # Сбор статистики
    stats = {
        'total_requests': requests.count(),
        'by_status': {},
        'by_priority': {},
        'by_product_type': {},
        'completion_rate': 0,
        'avg_completion_time': 0,
        'delayed_requests': 0
    }

    for request in requests:
        # По статусам
        stats['by_status'][request.status] = stats['by_status'].get(request.status, 0) + 1

        # По приоритетам
        stats['by_priority'][request.priority] = stats['by_priority'].get(request.priority, 0) + 1

        # По типам продукции
        stats['by_product_type'][request.product_type] = stats['by_product_type'].get(request.product_type, 0) + 1

        # Проверка задержек
        if request.deadline and request.status not in [RequestStatus.COMPLETED, RequestStatus.SHIPPED]:
            if timezone.now() > request.deadline:
                stats['delayed_requests'] += 1

    # Расчет процента завершения
    completed = stats['by_status'].get(RequestStatus.COMPLETED, 0)
    stats['completion_rate'] = (completed / stats['total_requests']) * 100 if stats['total_requests'] > 0 else 0

    return stats
