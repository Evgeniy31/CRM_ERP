from rest_framework import serializers
from .models import Request, Task, User, Comment, Notification


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'role', 'department', 'position', 'kpi_score', 'rating']


class RequestSerializer(serializers.ModelSerializer):
    manager = UserSerializer(read_only=True)
    supervisor = UserSerializer(read_only=True)
    customer = UserSerializer(read_only=True)

    class Meta:
        model = Request
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    request = RequestSerializer(read_only=True)
    executor = UserSerializer(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    request = RequestSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = '__all__'


class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    request = RequestSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = '__all__'
