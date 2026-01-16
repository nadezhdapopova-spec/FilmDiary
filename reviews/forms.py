from django import forms

from reviews.models import Review


class ReviewForm(forms.ModelForm):
    """Форма для создания и редактирования отзыва"""
    plot_rating = forms.FloatField(label="Сюжет", min_value=1, max_value=10)
    acting_rating = forms.FloatField(label="Актеры", min_value=1, max_value=10)
    directing_rating = forms.FloatField(label="Режиссура", min_value=1, max_value=10)
    visuals_rating = forms.FloatField(label="Визуал", min_value=1, max_value=10)
    soundtrack_rating = forms.FloatField(label="Саундтрек", min_value=1, max_value=10)

    class Meta:
        model = Review
        fields = ("watched_at", "number_of_views", "review")
        widgets = {
            "watched_at": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ["plot_rating", "acting_rating", "directing_rating",
                      "visuals_rating", "soundtrack_rating"]:
            self.fields[field].widget.attrs.update({
                "step": "0.1", "class": "rating-input"
            })

    def save(self, commit=True):
        """Вычисляет среднее 5 критериев оценки фильма и сохраняет в user_rating"""
        instance = super().save(commit=False)

        ratings = [
            self.cleaned_data["plot_rating"],
            self.cleaned_data["acting_rating"],
            self.cleaned_data["directing_rating"],
            self.cleaned_data["visuals_rating"],
            self.cleaned_data["soundtrack_rating"]
        ]
        instance.user_rating = sum(ratings) / len(ratings)

        if commit:
            instance.save()
        return instance
