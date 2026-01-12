from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from ..models import Request, Task, Comment, Notification, User, Role, RequestStatus, RequestPriority
from ..forms import RequestForm, TaskForm, CommentForm
from ..utils.notifications import send_notification
from ..utils.analytics import predict_completion_date
from ..utils.tasks import create_default_tasks


@login_required
def create_request(request):
    """Создание новой заявки"""
    if not request.user.can_create_request():
        messages.error(request, 'У вас нет прав для создания заявок')
        return redirect('dashboard')

    if request.method == 'POST':
        form = RequestForm(request.POST)
        if form.is_valid():
            # Создание заявки
            request_obj = form.save(commit=False)
            request_obj.manager = request.user
            request_obj.status = RequestStatus.PENDING_VALIDATION

            # Генерация номера заявки
            request_obj.request_number = request_obj.generate_request_number()

            # Расчет прогнозируемой даты завершения
            request_obj.estimated_completion = predict_completion_date(
                request_obj.product_type,
                request_obj.priority,
                request_obj.quantity
            )

            try:
                request_obj.save()

                # Отправка уведомления руководителю
                supervisors = User.objects.filter(role=Role.SUPERVISOR, is_verified=True)
                for supervisor in supervisors:
                    send_notification(
                        user=supervisor,
                        request=request_obj,
                        message=f'Новая заявка {request_obj.request_number} требует вашего одобрения',
                        notification_type='new_request'
                    )

                messages.success(request, f'Заявка {request_obj.request_number} успешно создана!')
                return redirect('view_request', request_id=request_obj.id)

            except Exception as e:
                messages.error(request, f'Ошибка при создании заявки: {str(e)}')

    else:
        form = RequestForm()

    return render(request, 'requests/create.html', {'form': form})


@login_required
def view_request(request, request_id):
    """Просмотр заявки"""
    request_obj = get_object_or_404(Request, id=request_id)

    # Проверка прав доступа
    if not (request.user == request_obj.manager or
            request.user == request_obj.supervisor or
            request.user.role == Role.ADMIN or
            request.user.role == Role.PRODUCTION_HEAD):
        messages.error(request, 'У вас нет доступа к этой заявке')
        return redirect('dashboard')

    comment_form = CommentForm()
    task_form = TaskForm()

    return render(request, 'requests/view.html', {
        'request': request_obj,
        'comment_form': comment_form,
        'task_form': task_form
    })


@login_required
def approve_request(request, request_id):
    """Одобрение заявки"""
    if not request.user.can_approve_request():
        messages.error(request, 'У вас нет прав для одобрения заявок')
        return redirect('dashboard')

    request_obj = get_object_or_404(Request, id=request_id)

    if request_obj.status != RequestStatus.PENDING_APPROVAL:
        messages.error(request, 'Заявка не ожидает одобрения')
        return redirect('view_request', request_id=request_id)

    request_obj.status = RequestStatus.APPROVED
    request_obj.supervisor = request.user
    request_obj.updated_at = timezone.now()
    request_obj.save()

    # Создание автоматических задач
    create_default_tasks(request_obj)

    # Отправка уведомлений
    send_notification(
        user=request_obj.manager,
        request=request_obj,
        message=f'Ваша заявка {request_obj.request_number} одобрена',
        notification_type='request_approved'
    )

    messages.success(request, 'Заявка успешно одобрена!')
    return redirect('view_request', request_id=request_id)


@login_required
def reject_request(request, request_id):
    """Отклонение заявки"""
    if not request.user.can_approve_request():
        messages.error(request, 'У вас нет прав для отклонения заявок')
        return redirect('dashboard')

    request_obj = get_object_or_404(Request, id=request_id)
    reason = request.POST.get('reason', '')

    request_obj.status = RequestStatus.CANCELLED
    request_obj.updated_at = timezone.now()
    request_obj.save()

    # Добавление комментария с причиной
    comment = Comment(
        request=request_obj,
        user=request.user,
        content=f'Заявка отклонена. Причина: {reason}',
        is_internal=True
    )
    comment.save()

    # Отправка уведомления
    send_notification(
        user=request_obj.manager,
        request=request_obj,
        message=f'Ваша заявка {request_obj.request_number} отклонена',
        notification_type='request_rejected'
    )

    messages.success(request, 'Заявка отклонена')
    return redirect('dashboard')


@login_required
def request_list(request):
    """Список заявок с фильтрацией"""
    page = request.GET.get('page', 1)
    status = request.GET.get('status', '')
    priority = request.GET.get('priority', '')

    # Базовый запрос в зависимости от роли
    if request.user.role == Role.MANAGER:
        queryset = Request.objects.filter(manager=request.user)
    elif request.user.role == Role.SUPERVISOR:
        queryset = Request.objects.filter(supervisor=request.user)
    elif request.user.role == Role.PRODUCTION_HEAD:
        queryset = Request.objects.filter(status__in=['in_progress', 'pending_materials'])
    elif request.user.role == Role.ADMIN:
        queryset = Request.objects.all()
    else:
        queryset = Request.objects.filter(manager=request.user)

    # Применение фильтров
    if status:
        queryset = queryset.filter(status=status)
    if priority:
        queryset = queryset.filter(priority=priority)

    # Сортировка и пагинация
    requests_page = Paginator(queryset.order_by('-created_at'), 20).get_page(page)

    return render(request, 'requests/list.html', {
        'requests': requests_page,
        'status': status,
        'priority': priority
    })


@login_required
def get_request_status(request, request_id):
    """API для получения статуса заявки"""
    request_obj = get_object_or_404(Request, id=request_id)

    # Проверка прав доступа
    if not (request.user == request_obj.manager or
            request.user == request_obj.customer or
            request.user.role == Role.ADMIN):
        return JsonResponse({'error': 'Access denied'}, status=403)

    return JsonResponse({
        'request_number': request_obj.request_number,
        'status': request_obj.status,
        'completion_percentage': request_obj.completion_percentage,
        'estimated_completion': request_obj.estimated_completion.isoformat() if request_obj.estimated_completion else None,
        'risk_level': request_obj.calculate_risk_level()
    })
