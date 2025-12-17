from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.urls import reverse
from django.utils.safestring import mark_safe

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    """Форма авторизации пользователя по email"""

    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите email",
                "autofocus": True,
            }
        ),
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Введите пароль",
            }
        ),
    )

    def confirm_login_allowed(self, user):
        """
        Вызывается Django после успешной аутентификации
        """
        if not user.is_active:
            raise forms.ValidationError(
                mark_safe(
                    f"Аккаунт не активирован. "
                    f"<a href='{reverse('users:resend_activation')}'>Запросите письмо активации</a>."
                ),
                code="inactive",
            )
