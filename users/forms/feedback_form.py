from django import forms

from users.models import MessageFeedback


class FeedbackForm(forms.ModelForm):
    """Класс формы обратной связи"""

    class Meta:
        model = MessageFeedback
        fields = ["name", "email", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.TextInput(attrs={"class": "form-control"}),
            "message": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
        }
