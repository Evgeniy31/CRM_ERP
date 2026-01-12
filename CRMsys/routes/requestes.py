from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from app import db
from models.request import Request, RequestStatus, Task, Comment
from models.user import User, Role
from forms import RequestForm, TaskForm, CommentForm
from utils.validators import validate_request_data
from utils.notifications import send_notification

requests_bp = Blueprint('requests', __name__)


@requests_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_request():
    """Создание новой заявки"""
    if not current_user.can_create_request():
        flash('У вас нет прав для создания заявок', 'error')
        return redirect(url_for('dashboard'))

    form = RequestForm()

    # Динамическое заполнение поля дедлайна
    if not form.deadline.data:
        form.deadline.data = datetime.utcnow() + timedelta(days=14)

    if form.validate_on_submit():
        # Валидация данных
        validation_result = validate_request_data(form.data)
        if not validation_result['valid']:
            for error in validation_result['errors']:
                flash(error, 'error')
            return render_template('requests/create.html', form=form)

        # Создание заявки
        request_obj = Request(
            title=form.title.data,
            description=form.description.data,
            product_type=form.product_type.data,
            quantity=form.quantity.data,
            priority=form.priority.data,
            deadline=form.deadline.data,
            manager_id=current_user.id,
            status=RequestStatus.PENDING_VALIDATION
        )

        # Генерация номера заявки
        request_obj.request_number = request_obj.generate_request_number()

        # Расчет прогнозируемой даты завершения
        from utils.analytics import predict_completion_date
        request_obj.estimated_completion = predict_completion_date(
            request_obj.product_type,
            request_obj.priority,
            request_obj.quantity
        )

        try:
            db.session.add(request_obj)
            db.session.commit()

            # Отправка уведомления руководителю
            supervisors = User.query.filter_by(role=Role.SUPERVISOR, is_active=True).all()
            for supervisor in supervisors:
                send_notification(
                    user_id=supervisor.id,
                    request_id=request_obj.id,
                    message=f'Новая заявка {request_obj.request_number} требует вашего одобрения',
                    notification_type='new_request'
                )

            flash(f'Заявка {request_obj.request_number} успешно создана!', 'success')
            return redirect(url_for('requests.view_request', request_id=request_obj.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при создании заявки: {str(e)}', 'error')

    return render_template('requests/create.html', form=form)


@requests_bp.route('/<int:request_id>')
@login_required
def view_request(request_id):
    """Просмотр заявки"""
    request_obj = Request.query.get_or_404(request_id)

    # Проверка прав доступа
    if not (current_user.id == request_obj.manager_id or
            current_user.id == request_obj.supervisor_id or
            current_user.role == Role.ADMIN or
            current_user.role == Role.PRODUCTION_HEAD):
        flash('У вас нет доступа к этой заявке', 'error')
        return redirect(url_for('dashboard'))

    comment_form = CommentForm()
    task_form = TaskForm()

    return render_template('requests/view.html',
                           request=request_obj,
                           comment_form=comment_form,
                           task_form=task_form)


@requests_bp.route('/<int:request_id>/approve', methods=['POST'])
@login_required
def approve_request(request_id):
    """Одобрение заявки"""
    if not current_user.can_approve_request():
        flash('У вас нет прав для одобрения заявок', 'error')
        return redirect(url_for('dashboard'))

    request_obj = Request.query.get_or_404(request_id)

    if request_obj.status != RequestStatus.PENDING_APPROVAL:
        flash('Заявка не ожидает одобрения', 'error')
        return redirect(url_for('requests.view_request', request_id=request_id))

    request_obj.status = RequestStatus.APPROVED
    request_obj.supervisor_id = current_user.id
    request_obj.updated_at = datetime.utcnow()

    # Создание автоматических задач
    from utils.tasks import create_default_tasks
    create_default_tasks(request_obj)

    # Отправка уведомлений
    send_notification(
        user_id=request_obj.manager_id,
        request_id=request_obj.id,
        message=f'Ваша заявка {request_obj.request_number} одобрена',
        notification_type='request_approved'
    )

    db.session.commit()
    flash('Заявка успешно одобрена!', 'success')
    return redirect(url_for('requests.view_request', request_id=request_id))


@requests_bp.route('/<int:request_id>/reject', methods=['POST'])
@login_required
def reject_request(request_id):
    """Отклонение заявки"""
    if not current_user.can_approve_request():
        flash('У вас нет прав для отклонения заявок', 'error')
        return redirect(url_for('dashboard'))

    request_obj = Request.query.get_or_404(request_id)
    reason = request.form.get('reason', '')

    request_obj.status = RequestStatus.CANCELLED
    request_obj.updated_at = datetime.utcnow()

    # Добавление комментария с причиной
    comment = Comment(
        request_id=request_obj.id,
        user_id=current_user.id,
        content=f'Заявка отклонена. Причина: {reason}',
        is_internal=True
    )
    db.session.add(comment)

    # Отправка уведомления
    send_notification(
        user_id=request_obj.manager_id,
        request_id=request_obj.id,
        message=f'Ваша заявка {request_obj.request_number} отклонена',
        notification_type='request_rejected'
    )

    db.session.commit()
    flash('Заявка отклонена', 'success')
    return redirect(url_for('dashboard'))


@requests_bp.route('/list')
@login_required
def request_list():
    """Список заявок с фильтрацией"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    priority = request.args.get('priority', '')

    # Базовый запрос в зависимости от роли
    if current_user.role == Role.MANAGER:
        query = Request.query.filter_by(manager_id=current_user.id)
    elif current_user.role == Role.SUPERVISOR:
        query = Request.query.filter_by(supervisor_id=current_user.id)
    elif current_user.role == Role.PRODUCTION_HEAD:
        query = Request.query.filter(Request.status.in_(['in_progress', 'pending_materials']))
    elif current_user.role == Role.ADMIN:
        query = Request.query
    else:
        query = Request.query.filter_by(manager_id=current_user.id)

    # Применение фильтров
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)

    # Сортировка и пагинация
    requests = query.order_by(Request.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )

    return render_template('requests/list.html',
                           requests=requests,
                           status=status,
                           priority=priority)


@requests_bp.route('/api/status/<int:request_id>')
@login_required
def get_request_status(request_id):
    """API для получения статуса заявки"""
    request_obj = Request.query.get_or_404(request_id)

    # Проверка прав доступа
    if not (current_user.id == request_obj.manager_id or
            current_user.id == request_obj.customer_id or
            current_user.role == Role.ADMIN):
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'request_number': request_obj.request_number,
        'status': request_obj.status,
        'completion_percentage': request_obj.completion_percentage,
        'estimated_completion': request_obj.estimated_completion.isoformat() if request_obj.estimated_completion else None,
        'risk_level': request_obj.calculate_risk_level()
    })