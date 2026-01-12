from django.urls import path

from reviews.views import WatchedListView, ReviewDetailView, ReviewUpdateView, ReviewDeleteView

app_name = "reviews"


urlpatterns = [
    path("reviews/", WatchedListView.as_view(), name="reviews"),
    path("reviews/<int:id>/", ReviewDetailView.as_view(), name="review_detail"),
    path("update/<int:id>/", ReviewUpdateView.as_view(), name="review_update"),
    path("delete/<int:id>/", ReviewDeleteView.as_view(), name="review_delete"),
]
