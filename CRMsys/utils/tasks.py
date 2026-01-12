from ..models import Task, User, Role


def create_default_tasks(request):
    """Создание автоматических задач для заявки"""
    # Задача на подготовку чертежей
    Task.objects.create(
        request=request,
        title='Подготовка чертежей и спецификаций',
        description='Создание технической документации для производства',
        executor=User.objects.filter(role=Role.DESIGN_HEAD).first(),
        priority='high',
        estimated_hours=8
    )

    # Задача на подготовку материалов
    Task.objects.create(
        request=request,
        title='Подготовка материалов и комплектующих',
        description='Закупка и подготовка необходимых материалов',
        executor=User.objects.filter(role=Role.PRODUCTION_HEAD).first(),
        priority='high',
        estimated_hours=4
    )

    # Задача на производство
    Task.objects.create(
        request=request,
        title='Изготовление изделия',
        description='Основной процесс производства',
        executor=User.objects.filter(role=Role.EXECUTOR).first(),
        priority='medium',
        estimated_hours=request.quantity * 2  # Примерная оценка
    )

    # Задача на контроль качества
    Task.objects.create(
        request=request,
        title='Контроль качества',
        description='Проверка готового изделия',
        executor=User.objects.filter(role=Role.PRODUCTION_HEAD).first(),
        priority='high',
        estimated_hours=2
    )
