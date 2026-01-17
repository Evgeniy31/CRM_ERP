from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .auth import login_view, logout_view, register_view
from .requestes import create_request, view_request, approve_request, reject_request, request_list, get_request_status
from .api import api_status, RequestViewSet, TaskViewSet, UserViewSet, CommentViewSet, NotificationViewSet

app_name = 'routes'

# DRF Router
router = DefaultRouter()
router.register(r'api/requests', RequestViewSet)
router.register(r'api/tasks', TaskViewSet)
router.register(r'api/users', UserViewSet)
router.register(r'api/comments', CommentViewSet)
router.register(r'api/notifications', NotificationViewSet)

urlpatterns = [
    # Include DRF router URLs
    path('', include(router.urls)),

    # Auth URLs
    path('auth/login/', login_view, name='login'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/register/', register_view, name='register'),

    # Request URLs
    path('create/', create_request, name='create_request'),
    path('<int:request_id>/', view_request, name='view_request'),
    path('<int:request_id>/approve/', approve_request, name='approve_request'),
    path('<int:request_id>/reject/', reject_request, name='reject_request'),
    path('list/', request_list, name='request_list'),

    # API URLs
    path('api/status/<int:request_id>/', get_request_status, name='get_request_status'),
    path('api/status/', api_status, name='api_status'),
]
