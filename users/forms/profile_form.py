from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm

from users.forms.register_form import CustomClearableFileInput
from users.validators import validate_avatar

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    """Форма для просмотра и изменения профиля пользователя"""

    username = forms.CharField(
        max_length=150, help_text="Не более 150 символов. Только буквы, цифры и символы @/./+/-/_."
    )
    avatar = forms.ImageField(required=False, validators=[validate_avatar])
    tg_chat_id = forms.IntegerField(required=False)

    class Meta:
        fields = [
            "username",
            "timezone",
            "tg_chat_id",
            "avatar",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "timezone": forms.Select(attrs={"class": "form-select"}),
            "tg_chat_id": forms.NumberInput(attrs={"class": "form-control"}),
            "avatar": CustomClearableFileInput(attrs={"class": "form-control"}),
        }


class UserPasswordForm(PasswordChangeForm):
    """Форма для смены пароля пользователя"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
