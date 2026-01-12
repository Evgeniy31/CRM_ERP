from django.urls import path
from . import views

app_name = 'routes'

urlpatterns = [
    path('create/', views.create_request, name='create_request'),
    path('<int:request_id>/', views.view_request, name='view_request'),
    path('<int:request_id>/approve/', views.approve_request, name='approve_request'),
    path('<int:request_id>/reject/', views.reject_request, name='reject_request'),
    path('list/', views.request_list, name='request_list'),
    path('api/status/<int:request_id>/', views.get_request_status, name='get_request_status'),
]
