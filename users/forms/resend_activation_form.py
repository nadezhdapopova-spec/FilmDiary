from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ResendActivationForm(forms.Form):
    """Форма отправки письма для активации профиля пользователя"""

    email = forms.EmailField(label="Email", widget=forms.EmailInput(attrs={
        "class": "form-control",
        "placeholder": "Введите ваш email",
    }))

    def clean_email(self):
        email = self.cleaned_data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise forms.ValidationError("Пользователь с таким email не найден")
        if user.is_active:
            raise forms.ValidationError("Ваш аккаунт уже активирован")
        self.user = user
        return email
