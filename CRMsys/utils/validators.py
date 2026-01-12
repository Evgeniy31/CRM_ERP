import re
from datetime import datetime


def validate_request_data(data):
    """Валидация данных заявки"""
    errors = []

    # Проверка обязательных полей
    required_fields = ['title', 'product_type', 'quantity', 'deadline']
    for field in required_fields:
        if not data.get(field):
            errors.append(f'Поле "{field}" обязательно для заполнения')

    # Валидация количества
    if data.get('quantity'):
        try:
            quantity = int(data['quantity'])
            if quantity <= 0:
                errors.append('Количество должно быть положительным числом')
            if quantity > 10000:
                errors.append('Количество не может превышать 10000')
        except ValueError:
            errors.append('Количество должно быть числом')

    # Валидация даты
    if data.get('deadline'):
        try:
            deadline = data['deadline']
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))

            if deadline < datetime.utcnow():
                errors.append('Срок выполнения не может быть в прошлом')

            if (deadline - datetime.utcnow()).days > 365:
                errors.append('Срок выполнения не может превышать 1 год')
        except (ValueError, TypeError):
            errors.append('Некорректный формат даты')

    # Валидация приоритета
    valid_priorities = ['low', 'medium', 'high', 'critical']
    if data.get('priority') and data['priority'] not in valid_priorities:
        errors.append(f'Приоритет должен быть одним из: {", ".join(valid_priorities)}')

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }


def validate_user_data(data):
    """Валидация данных пользователя"""
    errors = []

    # Валидация email
    if data.get('email'):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, data['email']):
            errors.append('Некорректный формат email')

    # Валидация телефона
    if data.get('phone'):
        phone_regex = r'^\+?[1-9]\d{1,14}$'
        if not re.match(phone_regex, data['phone'].replace(' ', '').replace('-', '')):
            errors.append('Некорректный формат телефона')

    # Валидация пароля
    if data.get('password'):
        password = data['password']
        if len(password) < 8:
            errors.append('Пароль должен содержать минимум 8 символов')
        if not any(c.isupper() for c in password):
            errors.append('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.isdigit() for c in password):
            errors.append('Пароль должен содержать хотя бы одну цифру')

    return {
        'valid': len(errors) == 0,
        'errors': errors
    }