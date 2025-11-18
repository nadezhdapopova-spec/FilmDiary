import os
from json import JSONDecodeError

import requests


from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE = "https://api.themoviedb.org/3"
LANG = "ru-RU"


class Tmdb:
    """Класс для получения информации о фильмах/сериалах через API сервиса TMDB"""
    def __init__(self) -> None:
        """Конструктор для получения вакансий через API"""
        self.base_url: str = BASE
        self.base_params: dict = {"api_key": API_KEY, "language": LANG}

    def _get_response(self, path, params=None):
        """Внутренняя функция для GET запросов"""
        url = f"{self.base_url}{path}"
        params = params or {}
        params.extend(self.base_params)

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            result = response.json()
        except requests.exceptions.RequestException:
            return {}
        except JSONDecodeError:
            return {}
        else:
            return result


    def search_movie(self, query, page=1):
        """Возвращает список фильмов по поисковой строке. Используется на странице поиска"""
        return self._get_response("/search/movie", {"query": query, "page": page})

    def get_movie_details(self, movie_id):
        """Возвращает подробную информацию о фильме. Используется в просмотре карточки фильма"""
        return self._get_response(f"/movie/{movie_id}", {"append_to_response": "images"})

    def get__config(self):
        """
        Возвращает конфигурацию TMDB для построения ссылки на постер:
        - base_url для изображений
        - размеры постеров
        - размеры backdrop
        """
        return self._get_response("/configuration", {})

    def get_credits(self, movie_id):
        """
        Возвращает актёров(cast) и команду(crew) для отображения актёров, режиссёров,
        сценаристов, продюсеров, операторов
        """
        return self._get_response(f"/movie/{movie_id}/credits", {})


# if __name__ == "__main__":
    # print(search_movie("Inception"))
    # print(get_movie_details("250845"))
