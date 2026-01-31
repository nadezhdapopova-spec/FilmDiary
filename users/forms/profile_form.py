from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm

from crispy_bootstrap5.bootstrap5 import FloatingField
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Layout, Row, Submit

from users.validators import validate_avatar, validate_telegram_id

User = get_user_model()


class CustomClearableFileInput(forms.ClearableFileInput):
    """Класс для создания кастомного поля формы для загрузки файлов"""

    template_name = "users/widgets/custom_file_input.html"


class UserProfileForm(forms.ModelForm):
    """Форма для просмотра и изменения профиля пользователя"""

    class Meta:
        model = User
        fields = ("username", "email", "timezone", "tg_chat_id", "avatar")
        widgets = {
            "avatar": CustomClearableFileInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column(FloatingField("username"), css_class="col-md-6"),
                Column(FloatingField("email"), css_class="col-md-6"),
            ),
            Row(
                Column(FloatingField("timezone"), css_class="col-md-6"),
                Column(FloatingField("tg_chat_id"), css_class="col-md-6"),
            ),
            Submit("save_profile", "Сохранить изменения", css_class="btn btn-primary w-100 mt-3"),
        )

    def clean_avatar(self):
        """Валидация аватара"""
        avatar = self.cleaned_data.get("avatar")
        if avatar:
            validate_avatar(avatar)
        return avatar

    def clean_tg_chat_id(self):
        """Валидация Телеграм id"""
        tg_chat_id = self.cleaned_data.get("tg_chat_id")
        if tg_chat_id:
            validate_telegram_id(tg_chat_id)
        return tg_chat_id

    def save(self, commit=True):
        """Сохранение данных"""
        user = super().save(commit=False)
        if "email" in self.changed_data:
            user.email_new = self.cleaned_data["email"]
            user.email_confirmed = False
            user.email = self.instance.email  # сохраняем старый email пока не подтвердят
        if commit:
            user.save()
        return user


class UserPasswordForm(PasswordChangeForm):
    """Форма для смены пароля пользователя"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.help_text = None

        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
