from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.validators import validate_telegram_id


User = get_user_model()


class RegisterForm(UserCreationForm):
    """Класс формы для регистрации пользователя"""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    tg_chat_id = forms.IntegerField(
        label="Telegram ID",
        required=False,
        validators=[validate_telegram_id],
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Например: 123456789",
            }
        ),
    )
    password1 = forms.CharField(
        label="Пароль",
        help_text="",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "id": "id_password1",
                "autocomplete": "new-password",
                "autocorrect": "off",
                "autocapitalize": "off",
                "spellcheck": "false",
            }
        ),
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        help_text="",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "username",
            "timezone",
            "tg_chat_id",
            "password1",
            "password2",
        )
        widgets = {
            "email": forms.TextInput(attrs={"class": "form-control"}),
            "timezone": forms.Select(attrs={"class": "form-select"}),
        }
