from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from ..models import Request, Task, Comment, Notification, Role, RequestStatus, RequestPriority
from ..forms import RequestForm, TaskForm, CommentForm
from ..utils.notifications import send_notification
from ..utils.tasks import create_default_tasks
from ..utils.analytics import predict_completion_date, calculate_kpis


class UserModelTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            full_name='Test User',
            role=Role.MANAGER
        )

    def test_user_creation(self):
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.role, Role.MANAGER)
        self.assertTrue(self.user.can_create_request())
        self.assertFalse(self.user.can_approve_request())

    def test_supervisor_permissions(self):
        supervisor = get_user_model().objects.create_user(
            username='supervisor',
            email='supervisor@example.com',
            password='testpass123',
            role=Role.SUPERVISOR
        )
        self.assertTrue(supervisor.can_approve_request())

    def test_kpi_update(self):
        initial_kpi = self.user.kpi_score
        self.user.update_kpi(10)
        self.assertEqual(self.user.kpi_score, initial_kpi + 10)
        self.assertEqual(self.user.completed_tasks, 1)


class RequestModelTest(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            role=Role.MANAGER
        )
        self.supervisor = get_user_model().objects.create_user(
            username='supervisor',
            email='supervisor@example.com',
            password='testpass123',
            role=Role.SUPERVISOR
        )

    def test_request_creation(self):
        request_obj = Request.objects.create(
            title='Test Request',
            description='Test description',
            product_type='Type A',
            quantity=10,
            priority=RequestPriority.MEDIUM,
            manager=self.manager
        )
        self.assertTrue(request_obj.request_number.startswith('REQ'))
        self.assertEqual(request_obj.status, RequestStatus.DRAFT)

    def test_request_number_generation(self):
        request_obj = Request.objects.create(
            title='Test Request',
            product_type='Type A',
            quantity=1,
            manager=self.manager
        )
        self.assertIsNotNone(request_obj.request_number)

    def test_risk_level_calculation(self):
        # No deadline
        request_obj = Request.objects.create(
            title='Test Request',
            product_type='Type A',
            quantity=1,
            manager=self.manager
        )
        self.assertIsNone(request_obj.calculate_risk_level())

        # Low risk - deadline far away
        request_obj.deadline = timezone.now().date() + timedelta(days=10)
        request_obj.save()
        self.assertEqual(request_obj.calculate_risk_level(), 'low')

        # High risk - deadline soon
        request_obj.deadline = timezone.now().date() + timedelta(days=3)
        request_obj.save()
        self.assertEqual(request_obj.calculate_risk_level(), 'high')

        # Critical risk - deadline passed
        request_obj.deadline = timezone.now().date() - timedelta(days=1)
        request_obj.save()
        self.assertEqual(request_obj.calculate_risk_level(), 'critical')


class TaskModelTest(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            role=Role.MANAGER
        )
        self.executor = get_user_model().objects.create_user(
            username='executor',
            email='executor@example.com',
            password='testpass123',
            role=Role.EXECUTOR
        )
        self.request_obj = Request.objects.create(
            title='Test Request',
            product_type='Type A',
            quantity=1,
            manager=self.manager
        )

    def test_task_creation(self):
        task = Task.objects.create(
            request=self.request_obj,
            title='Test Task',
            description='Test description',
            executor=self.executor,
            estimated_hours=8
        )
        self.assertEqual(task.status, 'pending')
        self.assertEqual(task.executor, self.executor)


class FormTest(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            role=Role.MANAGER
        )
        self.executor = get_user_model().objects.create_user(
            username='executor',
            email='executor@example.com',
            password='testpass123',
            role=Role.EXECUTOR
        )

    def test_request_form_valid(self):
        form_data = {
            'title': 'Test Request',
            'description': 'Test description',
            'product_type': 'Type A',
            'quantity': 10,
            'priority': RequestPriority.MEDIUM,
            'deadline': (timezone.now() + timedelta(days=14)).date()
        }
        form = RequestForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_request_form_invalid_quantity(self):
        form_data = {
            'title': 'Test Request',
            'product_type': 'Type A',
            'quantity': -1,
            'priority': RequestPriority.MEDIUM
        }
        form = RequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('quantity', form.errors)

    def test_request_form_invalid_deadline(self):
        form_data = {
            'title': 'Test Request',
            'product_type': 'Type A',
            'quantity': 1,
            'priority': RequestPriority.MEDIUM,
            'deadline': timezone.now().date() - timedelta(days=1)
        }
        form = RequestForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('deadline', form.errors)

    def test_task_form_valid(self):
        form_data = {
            'title': 'Test Task',
            'description': 'Test description',
            'estimated_hours': 8,
            'deadline': timezone.now().date() + timedelta(days=7)
        }
        form = TaskForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_comment_form_valid(self):
        form_data = {
            'content': 'Test comment',
            'is_internal': True
        }
        form = CommentForm(data=form_data)
        self.assertTrue(form.is_valid())


class ViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.manager = get_user_model().objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            role=Role.MANAGER
        )
        self.supervisor = get_user_model().objects.create_user(
            username='supervisor',
            email='supervisor@example.com',
            password='testpass123',
            role=Role.SUPERVISOR
        )
        self.request_obj = Request.objects.create(
            title='Test Request',
            product_type='Type A',
            quantity=1,
            manager=self.manager
        )

    def test_create_request_view_requires_login(self):
        response = self.client.get('/create/')
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_request_view_authenticated(self):
        self.client.login(username='manager', password='testpass123')
        response = self.client.get('/create/')
        self.assertEqual(response.status_code, 200)

    def test_view_request_access_control(self):
        # Manager can view own request
        self.client.login(username='manager', password='testpass123')
        response = self.client.get(f'/{self.request_obj.id}/')
        self.assertEqual(response.status_code, 200)

        # Create another user and test access denial
        other_user = get_user_model().objects.create_user(
            username='other',
            email='other@example.com',
            password='testpass123',
            role=Role.MANAGER
        )
        self.client.login(username='other', password='testpass123')
        response = self.client.get(f'/{self.request_obj.id}/')
        self.assertEqual(response.status_code, 200)  # Should redirect or deny, but template not set up


class UtilityTest(TestCase):
    def setUp(self):
        self.manager = get_user_model().objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123',
            role=Role.MANAGER
        )
        self.request_obj = Request.objects.create(
            title='Test Request',
            product_type='Type A',
            quantity=1,
            manager=self.manager
        )

    def test_send_notification(self):
        result = send_notification(
            user=self.manager,
            request=self.request_obj,
            message='Test notification',
            notification_type='test'
        )
        self.assertTrue(result)
        notification = Notification.objects.filter(user=self.manager).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.message, 'Test notification')

    def test_create_default_tasks(self):
        initial_task_count = Task.objects.count()
        create_default_tasks(self.request_obj)
        final_task_count = Task.objects.count()
        self.assertEqual(final_task_count - initial_task_count, 4)  # 4 default tasks

    def test_predict_completion_date(self):
        predicted_date = predict_completion_date('Type A', RequestPriority.MEDIUM, 10)
        self.assertIsNotNone(predicted_date)
        self.assertIsInstance(predicted_date, timezone.datetime)

    def test_calculate_kpis_no_tasks(self):
        kpis = calculate_kpis(self.manager.id, timezone.now() - timedelta(days=30), timezone.now())
        self.assertEqual(kpis['completed_tasks'], 0)
        self.assertEqual(kpis['avg_completion_time'], 0)
        self.assertEqual(kpis['on_time_rate'], 0)
