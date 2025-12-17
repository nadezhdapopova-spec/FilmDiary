import os
import time
from json import JSONDecodeError

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3"
LANG = "ru-RU"


class Tmdb:
    """Класс для работы с TMDB API"""

    def __init__(self) -> None:
        """Конструктор для получения вакансий через API"""
        self._base_url: str = BASE
        self._base_params: dict = {"api_key": API_KEY, "language": LANG}

    def _get(self, path: str, params: dict | None = None, retries=3, timeout=5) -> dict:
        """
        Внутренний метод для GET запросов:
        timeout: 5 сек (защита от зависания)
        retries: 3 попытки
        """
        url = f"{self._base_url}{path}"
        params = {**self._base_params, **(params or {})}

        for attempt in range(1, retries + 1):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                return response.json()

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < retries:
                    time.sleep(2 ** (attempt - 1))  # Backoff: 1s → 2s → 4s
                    continue
                return {}
            except requests.exceptions.HTTPError as e:
                status = e.response.status_code
                if status in (429, 500, 502, 503, 504):
                    if attempt < retries:
                        time.sleep(2 ** (attempt - 1))
                        continue
                    return {}
                return {}
            except JSONDecodeError:
                return {}
        return {}

    def _get_multipage(self, path: str, pages: int = 1, params=None) -> list:
        """Возвращает несколько страниц результатов"""
        all_results = []
        params = params or {}

        first = self._get(path, {**params, "page": 1})
        if "results" not in first:
            return []

        all_results.extend(first["results"])
        total_pages = first.get("total_pages", 1)
        pages_to_fetch = min(pages, total_pages)

        for page in range(2, pages_to_fetch + 1):
            resp = self._get(path, {**params, "page": page})
            if "results" in resp:
                all_results.extend(resp["results"])
            else:
                break
        return all_results

    def search_movie(self, query, page=1):
        """Возвращает список фильмов по поисковой строке. Используется на странице поиска"""
        return self._get("/search/movie", {"query": query, "page": page})

    def get_movie_details(self, movie_id):
        """Возвращает подробную информацию о фильме. Используется в просмотре карточки фильма"""
        return self._get(
            f"/movie/{movie_id}", {"append_to_response": "images", "include_image_language": "en-US,null"}
        )

    def get_config(self):
        """
        Возвращает конфигурацию TMDB для построения ссылки на постер:
        - base_url для изображений
        - размеры постеров
        - размеры backdrop
        """
        return self._get("/configuration", {})

    def get_credits(self, movie_id):
        """
        Возвращает актёров(cast) и команду(crew) для отображения актёров, режиссёров,
        сценаристов, продюсеров, операторов
        """
        return self._get(f"/movie/{movie_id}/credits", {})

    def get_now_playing(self, pages=1):
        """Возвращает фильмы, которые сейчас в кино"""
        return self._get_multipage("/movie/now_playing", pages)

    def get_upcoming(self, pages=1):
        """Возвращает фильмы, которые скоро выйдут в прокат"""
        return self._get_multipage("/movie/upcoming", pages)
        # return [r.get("title") for r in res.get("results")]

    def get_popular(self, pages=1):
        """Возвращает популярные фильмы"""
        return self._get_multipage("/movie/popular", pages)

    def get_trending(self, time_window="week"):
        """Возвращает трендовые фильмы ('тренды недели')"""
        return self._get(f"/trending/movie/{time_window}")

    def get_top_rated(self, pages=1):
        """Возвращает топ-рейтинговые фильмы"""
        return self._get_multipage("/movie/top_rated", pages)

    def get_similar_movies(self, movie_id, pages=1):
        """Возвращает похожие фильмы (по содержанию)"""
        return self._get_multipage(f"/movie/{movie_id}/similar", pages)

    def get_recommended_movies(self, movie_id, pages=1):
        """Возвращает рекомендации TMDB на основе их алгоритма (collaborative + content-based)"""
        return self._get_multipage(f"/movie/{movie_id}/recommendations", pages)

    def get_genres(self):
        """Возвращает список жанров"""
        return self._get("/genre/movie/list")

    def get_movies_by_genre(self, genre_id, page=1):
        """Возвращает фильмы по жанру"""
        return self._get("/discover/movie", {"with_genres": genre_id, "page": page})


if __name__ == "__main__":
    tmdb = Tmdb()
    # print(tmdb.search_movie("Битва за битвой", 1))
    # print(tmdb.get_movie_details("1054867"))
    # print(tmdb.get_config())
    # print(tmdb.get_credits("1054867"))
    # print([r for r in res.get("cast")][0])
    # print([res.keys()])
    # print(tmdb.get_now_playing(3))
    # print(tmdb.get_upcoming(3))
    # print(tmdb.get_popular(3))
    # print(tmdb.get_trending())
    # print(tmdb.get_top_rated(3))
    # print(tmdb.get_similar_movies("280", 2))
    # print(tmdb.get_recommended_movies("280", 2))
    # print(tmdb.get_genres())
    print(tmdb.get_movies_by_genre("35", 1))


# configs = {'change_keys': ['adult', 'air_date', 'also_known_as', 'alternative_titles', 'biography', 'birthday', 'budget', 'cast', 'certifications', 'character_names', 'created_by', 'crew', 'deathday', 'episode', 'episode_number', 'episode_run_time', 'freebase_id', 'freebase_mid', 'general', 'genres', 'guest_stars', 'homepage', 'images', 'imdb_id', 'languages', 'name', 'network', 'origin_country', 'original_name', 'original_title', 'overview', 'parts', 'place_of_birth', 'plot_keywords', 'production_code', 'production_companies', 'production_countries', 'releases', 'revenue', 'runtime', 'season', 'season_number', 'season_regular', 'spoken_languages', 'status', 'tagline', 'title', 'translations', 'tvdb_id', 'tvrage_id', 'type', 'video', 'videos'], 'images': {'base_url': 'http://image.tmdb.org/t/p/', 'secure_base_url': 'https://image.tmdb.org/t/p/', 'backdrop_sizes': ['w300', 'w780', 'w1280', 'original'], 'logo_sizes': ['w45', 'w92', 'w154', 'w185', 'w300', 'w500', 'original'], 'poster_sizes': ['w92', 'w154', 'w185', 'w342', 'w500', 'w780', 'original'], 'profile_sizes': ['w45', 'w185', 'h632', 'original'], 'still_sizes': ['w92', 'w185', 'w300', 'original']}}
# genres = {'genres': [{'id': 28, 'name': 'боевик'}, {'id': 12, 'name': 'приключения'}, {'id': 16, 'name': 'мультфильм'}, {'id': 35, 'name': 'комедия'}, {'id': 80, 'name': 'криминал'}, {'id': 99, 'name': 'документальный'}, {'id': 18, 'name': 'драма'}, {'id': 10751, 'name': 'семейный'}, {'id': 14, 'name': 'фэнтези'}, {'id': 36, 'name': 'история'}, {'id': 27, 'name': 'ужасы'}, {'id': 10402, 'name': 'музыка'}, {'id': 9648, 'name': 'детектив'}, {'id': 10749, 'name': 'мелодрама'}, {'id': 878, 'name': 'фантастика'}, {'id': 10770, 'name': 'телевизионный фильм'}, {'id': 53, 'name': 'триллер'}, {'id': 10752, 'name': 'военный'}, {'id': 37, 'name': 'вестерн'}]}
# credits_cast = {'Acting'}
# credits_job_crew = {'Director', 'Producer', 'Writer', 'Original Music Composer'}
