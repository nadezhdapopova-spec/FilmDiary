from django import forms

from reviews.models import Review
from reviews.validators import validate_number_of_views


class ReviewForm(forms.ModelForm):
    """Форма для создания и редактирования отзыва"""
    plot_rating = forms.FloatField(label="Сюжет", min_value=1, max_value=10)
    acting_rating = forms.FloatField(label="Актеры", min_value=1, max_value=10)
    directing_rating = forms.FloatField(label="Режиссура", min_value=1, max_value=10)
    visuals_rating = forms.FloatField(label="Визуал", min_value=1, max_value=10)
    soundtrack_rating = forms.FloatField(label="Саундтрек", min_value=1, max_value=10)
    number_of_views = forms.IntegerField(validators=[validate_number_of_views], required=False)

    class Meta:
        model = Review
        fields = (
            "watched_at",
            "number_of_views",
            "plot_rating",
            "acting_rating",
            "directing_rating",
            "visuals_rating",
            "soundtrack_rating",
            "review",
        )
        widgets = {
            "watched_at": forms.DateInput(attrs={"type": "date"}),
        }
