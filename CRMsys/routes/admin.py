from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from models.models import User, Request, Task, Comment, Notification

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'full_name', 'department', 'is_active')
    list_filter = ('role', 'department', 'is_active', 'is_verified')
    search_fields = ('username', 'email', 'full_name')
    ordering = ('username',)

    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'full_name', 'department', 'position', 'phone', 'kpi_score', 'rating', 'completed_tasks', 'is_verified')}),
    )

@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ('request_number', 'title', 'status', 'priority', 'manager', 'created_at')
    list_filter = ('status', 'priority', 'product_type')
    search_fields = ('request_number', 'title', 'description')
    ordering = ('-created_at',)

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'request', 'executor', 'status', 'priority', 'deadline')
    list_filter = ('status', 'priority')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'request', 'user', 'content', 'is_internal', 'created_at')
    list_filter = ('is_internal',)
    search_fields = ('content',)
    ordering = ('-created_at',)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('message',)
    ordering = ('-created_at',)
