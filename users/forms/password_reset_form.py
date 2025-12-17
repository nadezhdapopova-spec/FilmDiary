from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm

User = get_user_model()


class CustomPasswordResetForm(PasswordResetForm):
    """Форма для восстановления пароля"""

    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "autocomplete": "email",
            }
        ),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]

        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким email не найден")

        return email


class CustomSetPasswordForm(SetPasswordForm):
    """Форма для нового пароля"""

    new_password1 = forms.CharField(
        label="Новый пароль",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="",
    )
    new_password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
            }
        ),
        help_text="",
    )
