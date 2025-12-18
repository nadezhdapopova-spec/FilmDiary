from django.urls import path

from films.views import UserListFilmView, FilmDetailView, AddFilmView, DeleteFilmView

app_name = "films"

urlpatterns = [
    path("home/", UserListFilmView.as_view(template_name="films/home.html"), name="home"),
    path("my_films/", UserListFilmView.as_view(template_name="films/my_films.html"), name="my_films"),
    path("film/<int:tmdb_id>/", FilmDetailView.as_view(), name="film_detail"),
    path("add/", AddFilmView.as_view(), name="add_film"),
    path("delete/<int:tmdb_id>/", DeleteFilmView.as_view(), name="delete_film"),
]