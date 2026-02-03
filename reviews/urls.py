from django.urls import path

from reviews.views import (
    ReviewCreateView,
    ReviewDeleteView,
    ReviewDetailView,
    ReviewsListView,
    ReviewUpdateView,
    WatchedListView,
)

app_name = "reviews"


urlpatterns = [
    path("watched/", WatchedListView.as_view(), name="watched"),
    path("reviews/", ReviewsListView.as_view(), name="reviews"),
    path("reviews/<int:pk>/", ReviewDetailView.as_view(), name="review_detail"),
    path("create/<int:tmdb_id>/", ReviewCreateView.as_view(), name="review_create"),
    path("update/<int:pk>/", ReviewUpdateView.as_view(), name="review_update"),
    path("<int:pk>/delete/", ReviewDeleteView.as_view(), name="review_delete"),
]
