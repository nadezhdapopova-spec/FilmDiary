from django.urls import path

from films.views import UserListFilmView, FilmDetailView, AddFilmView, DeleteFilmView, HomeView, film_search_view, \
    UpdateFilmStatusView, FavoriteFilmsView, FilmRecommendsView

app_name = "films"

urlpatterns = [
    path("home/", HomeView.as_view(), name="home"),
    path("recommends/", FilmRecommendsView.as_view(), name="recommends"),
    path("search/", film_search_view, name="film_search"),
    path("my_films/", UserListFilmView.as_view(), name="my_films"),
    path("favorite/", FavoriteFilmsView.as_view(), name="favorite_films"),
    path("film/<int:tmdb_id>/", FilmDetailView.as_view(), name="film_detail"),
    path("add_film/", AddFilmView.as_view(), name="add_film"),
    path("update-status/", UpdateFilmStatusView.as_view(), name="update_status"),
    path("<int:tmdb_id>/delete/", DeleteFilmView.as_view(), name="delete_film"),
]