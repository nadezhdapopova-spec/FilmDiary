from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError


User = get_user_model()


class CustomPasswordResetForm(PasswordResetForm):
    """Класс восстановления пароля пользователя"""

    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-control"}))

    def clean_email(self):
        """Валидация указанного email пользователя"""
        email = self.cleaned_data.get("email")
        if not User.objects.filter(email=email).exists():
            raise ValidationError("Пользователь с таким email не найден")
        return email

    def save(self, *args, **kwargs):
        """Использование кастомного письма для восстановления пароля пользователя"""
        kwargs["html_email_template_name"] = "users/password_reset_email.html"
        return super().save(*args, **kwargs)


class CustomSetPasswordForm(SetPasswordForm):
    """Класс для создания и сохранения нового пароля пользователя"""

    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Новый пароль"}))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Подтвердите пароль"}))
