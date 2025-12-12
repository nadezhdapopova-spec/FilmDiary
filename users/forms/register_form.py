from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.forms import UserCreationForm

from users.validators import validate_avatar

User = get_user_model()


class CustomClearableFileInput(forms.ClearableFileInput):
    """Класс для создания кастомного поля формы для загрузки файлов"""

    template_name = "users/widgets/custom_file_input.html"


class RegisterForm(UserCreationForm):
    """Класс формы для регистрации пользователя"""

    username = forms.CharField(
        max_length=150, help_text="Не более 150 символов. Только буквы, цифры и символы @/./+/-/_."
    )
    avatar = forms.ImageField(required=False, validators=[validate_avatar])
    tg_chat_id = forms.IntegerField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "username",
            "timezone",
            "tg_chat_id",
            "avatar",
            "password1",
            "password2",
        )
        widgets = {
            "email": forms.TextInput(attrs={"class": "form-control"}),
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "timezone": forms.Select(attrs={"class": "form-select"}),
            "tg_chat_id": forms.NumberInput(attrs={"class": "form-control"}),
            "avatar": CustomClearableFileInput(attrs={"class": "form-control"}),
            "password1": forms.PasswordInput(attrs={"class": "form-control"}),
            "password2": forms.PasswordInput(attrs={"class": "form-control"}),
        }
