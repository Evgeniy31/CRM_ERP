from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from datetime import datetime
from .models import User, Request, Task, Comment, Role, RequestPriority


class LoginForm(AuthenticationForm):
    remember_me = forms.BooleanField(required=False, label='Запомнить меня')

    class Meta:
        fields = ['username', 'password', 'remember_me']


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    full_name = forms.CharField(max_length=150, label='ФИО')
    role = forms.ChoiceField(choices=Role.choices, label='Роль')
    department = forms.CharField(max_length=100, required=False, label='Отдел')
    position = forms.CharField(max_length=100, required=False, label='Должность')

    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'password1', 'password2', 'role', 'department', 'position']


class RequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['title', 'description', 'product_type', 'quantity', 'priority', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['deadline'].initial = (timezone.now() + timezone.timedelta(days=14)).date()

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise forms.ValidationError('Количество должно быть положительным числом')
        return quantity

    def clean_deadline(self):
        deadline = self.cleaned_data.get('deadline')
        if deadline and deadline < timezone.now().date():
            raise forms.ValidationError('Срок выполнения не может быть в прошлом')
        return deadline


class TaskForm(forms.ModelForm):
    executor = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=[Role.EXECUTOR, Role.PRODUCTION_HEAD, Role.DESIGN_HEAD]),
        required=False,
        empty_label="Выберите исполнителя",
        label='Исполнитель'
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'executor', 'estimated_hours', 'deadline', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'deadline': forms.DateInput(attrs={'type': 'date'}),
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'is_internal']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3}),
        }
