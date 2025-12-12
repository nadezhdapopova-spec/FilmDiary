from django.contrib.auth import get_user_model
from django import forms
from django.contrib.auth.forms import UserCreationForm


User = get_user_model()


class CustomClearableFileInput(forms.ClearableFileInput):
    """Класс для создания кастомного поля формы для загрузки файлов"""

    template_name = "users/widgets/custom_file_input.html"


class RegisterForm(UserCreationForm):
    """Класс формы для регистрации пользователя"""

    username = forms.CharField(
        max_length=150, help_text="Не более 150 символов. Только буквы, цифры и символы @/./+/-/_."
    )

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

    def clean_avatar(self):
        """Метод валидации поля формы 'аватар' на формат и размер файла"""
        avatar = self.cleaned_data.get("avatar")
        if not avatar or isinstance(avatar, str):
            return avatar
        valid_content_types = ["image/jpeg", "image/png"]
        if avatar.content_type not in valid_content_types:
            raise forms.ValidationError("Файл должен быть в формате JPEG или PNG")
        valid_extensions = [".jpg", ".jpeg", ".png"]
        import os

        ext = os.path.splitext(avatar.name)[1].lower()
        if ext not in valid_extensions:
            raise forms.ValidationError("Недопустимое расширение файла. Используйте JPG или PNG")
        max_size_mb = 5
        if avatar.size > max_size_mb * 1024 * 1024:
            raise forms.ValidationError(f"Размер файла не должен превышать {max_size_mb} МБ")
        return avatar
