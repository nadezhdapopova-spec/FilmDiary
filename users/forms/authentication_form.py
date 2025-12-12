from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomAuthenticationForm(AuthenticationForm):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "Введите email",
        })
    )
    password = forms.CharField(
        label="Пароль",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Введите пароль",
        }),
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get("email")
        password = cleaned_data.get("password")

        if email and password:
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise forms.ValidationError("Пользователь с таким email не найден")

            if not user.check_password(password):
                raise forms.ValidationError("Неверный пароль")

            if not user.is_active:
                raise forms.ValidationError(
                    "Аккаунт не активирован. Проверьте почту или запросите повторное письмо активации"
                )

            self.user = user  # Сохраняем пользователя для логина в view

        return cleaned_data

    def get_user(self):
        """Возвращает пользователя для LoginView"""
        return getattr(self, "user", None)
