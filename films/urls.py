from django.urls import path

from films.views import UserListFilmView, FilmDetailView, AddFilmView, DeleteFilmView

app_name = "films"

urlpatterns = [
    path("my_films/", UserListFilmView.as_view(), name="my_films"),
    path("film/<int:tmdb_id>/", FilmDetailView.as_view(), name="film_detail"),
    path("add/", AddFilmView.as_view(), name="add_film"),
    path("delete/<int:tmdb_id>/", DeleteFilmView.as_view(), name="delete_film"),
]