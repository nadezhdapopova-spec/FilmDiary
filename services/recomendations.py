import math
from collections import defaultdict
from datetime import datetime
import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class FeatureCache:
    """Кэширование признаков фильмов, чтобы не вычислять заново"""

    def __init__(self):
        self.cache = {}

    def get(self, movie):
        if movie.id not in self.cache:
            self.cache[movie.id] = set(movie.feature_set)
        return self.cache[movie.id]


class InvertedIndex:
    """
    Обратный индекс: feature -> {movie_ids}.
    Находит все фильмы, которые имеют хотя бы один заданный признак, не перебирая весь каталог:
    сопоставляет каждый признак (feature) со множеством идентификаторов фильмов, которые содержат этот признак
    """

    def __init__(self) -> None:
        self.index = defaultdict(set)

    def add_movie(self, movie_id: str, feature_set: set) -> None:
        """
        Фильмы:
        movie 1: feature_set = {"genre:Sci-Fi", "actor:Tom Hardy", "director:Nolan"}
        movie 2: feature_set = {"genre:Drama", "actor:DiCaprio", "director:Nolan"}
        movie 3: feature_set = {"genre:Sci-Fi", "actor:DiCaprio", "director:Somebody"}
        movie 4: feature_set = {"genre:Comedy", "actor:Someone", "director:SomeoneElse"}
        Просмотрен movie 1 ->
        self.index = {"genre:Sci-Fi": {1, 3}, "actor:Tom Hardy": {1},
                      "director:Nolan": {1, 2}, "genre:Drama": {2},
                      "actor:DiCaprio": {2,3}, "genre:Comedy": {4},...}
        """
        for f in feature_set:
            self.index[f].add(movie_id)

    def candidates_for(self, feature_set: set) -> set:
        """
        Возвращает set кандидатов, которые совпадают хотя бы по одному признаку.
        Оператор |= (in-place union) добавляет все id из self.index[f] в cand:
        {1,2,3}
        """
        cand = set()
        for f in feature_set:
            cand |= self.index.get(f, set())
        return cand


class TextSimilarity:
    """Вычисляет косинусное сходство между текстами с использованием TF-IDF"""

    def __init__(self, movies: list) -> None:
        """
        Инициализация атрибутов класса:
        movies — список фильмов ORM
        texts — список кортежей для каждого фильма(id, описание, ключевой тэг)
        """
        texts = [
            (m.id, (m.overview or "") + " " + (m.tagline or ""))
            for m in movies
        ]
        self.ids = [m[0] for m in texts]
        content = [m[1] for m in texts]

        self.vectorizer = TfidfVectorizer(max_features=5000)  # преобразует тексты в TF-IDF векторы
        self.matrix = self.vectorizer.fit_transform(content)  # матрица веса слов в текстах

    def similarity(self, id_a: str, id_b: str) -> int | float:
        """Вычисляет косинусное сходство между двумя текстами"""
        try:
            idx_a = self.ids.index(id_a)  # индексная позиция конкретного текста
            idx_b = self.ids.index(id_b)
        except ValueError:
            return 0

        v1 = self.matrix[idx_a]   # матрица веса слов конкретного текста по индексной позиции
        v2 = self.matrix[idx_b]
        return cosine_similarity(v1, v2)[0][0]  # косинусное сходство между двумя текстами


FEATURE_WEIGHTS = {
    "director": 3.0,
    "actor": 2.0,
    "genre": 1.5,
    "keyword": 1.0,
}

def feature_weight(f: str) -> float:
    """
    Принимает строку формата '<тип>:<значение>'(например 'actor:Tom Hardy'
    Возвращает вес из FEATURE_WEIGHTS по типу признака (actor/genre/director) или дефолтный(1)"""
    if not f: return 1
    f_type = f.split(":", 1)[0]
    return FEATURE_WEIGHTS.get(f_type, 1)


def jaccard_weighted(set_a: set, set_b: set) -> float:
    """
    Принимает множество признаков set_a(фильм_А) и set_b(фильм_B), каждый признак — строка типа 'actor:Tom Hardy'.
    Возвращает взвешенный Jaccard (суммарный вес общих признаков делённый на суммарный вес всех признаков)
    """
    inter = set_a & set_b  # пересечения
    union = set_a | set_b  # уникальные признаки

    inter_w = sum(feature_weight(f) for f in inter)  # сумма весов всех пересечений
    union_w = sum(feature_weight(f) for f in union)  # сумма весов всех уникальных признаков

    return inter_w / union_w if union_w else 0


def normalize_rating(rating: int) -> float:
    """Нормализация рейтинга пользователя от 1..10 -> 0..1"""
    rating = max(1, min(10, rating))
    return (rating - 1) / 9


def recency_boost(date_watched: datetime.date) -> float:
    """
    Делает вежие фильмы важнее.
    Логарифмическая декрементация: даёт умеренно-быстрое уменьшение влияния старых оценок,
    но не экспоненциальное и не слишком резкое.
    """
    days = (datetime.now().date() - date_watched).days if date_watched <= datetime.now() else 0
    return 1 / (1 + math.log1p(days))   # 1/(1+ln(1+days))


def build_recommendations(user, all_movies: list):
    """
    Основной алгоритм рекомендаций, формирует персональные рекомендации для user на основе:
    - признаков просмотренных фильмов (genre / actor / director / keywords и т.д.),
    - текстового сходства (TF-IDF по overview/tagline),
    - нормализованных оценок пользователя,
    - свежести оценок (recency boost),
    - explainability (почему рекомендация получена).
    Функция возвращает отсортированный список рекомендаций
    с movie_id, нормализованным score и списком вкладов/объяснений
    """
    feature_cache = FeatureCache()  # Создаётся экземпляр кэша признаков, хранит в памяти movie_id -> feature_set,
                                    # чтобы не пересчитывать признаки для одного фильма многократно

    watched = {r.film_id for r in user.reviews.all()}  # собирает id просмотренных фильмов (watched: set)

    inv = InvertedIndex()  # создает инвертированный индекс (feature → множество movie_id)
    for movie in all_movies:
        inv.add_movie(movie.id, feature_cache.get(movie))

    textsim = TextSimilarity(all_movies)  # вызван TF-IDF модуль

    scores = defaultdict(float)  # словарь movie_id -> накопленный score (float)
    reasons = defaultdict(list)  # словарь movie_id -> list of dict: id фильма и объяснение, почему рекомендует его по вкладу

    for review in user.reviews.all():  # цикл по всем просмотренным фильмам
        film = review.film
        user_features = feature_cache.get(film)

        nr = normalize_rating(review.rating)  # нормализованная оценка пользователя в диапазон [0,1]
        rec = recency_boost(review.created_at.date()) # коэффициент свежести

        cand_ids = inv.candidates_for(user_features)  # кандидаты: фильмы, совпадающие по признакам
        cand_ids -= watched  # исключить уже просмотренные

        for cid in cand_ids:
            candidate = next(m for m in all_movies if m.id == cid)  # для id кандидата cid получаем сам объект candidate: линейный поиск next(...) по all_movies
            cand_features = feature_cache.get(candidate)  # feature_set для кандидата

            sim_struct = jaccard_weighted(user_features, cand_features) # вес кандидата по отношению к просмотренному фильму, чем больше совпадающих (и редких/важных) признаков — тем выше sim_struct

            sim_text = textsim.similarity(film.id, cid)  # TF-IDF similarity: косинусное сходство между двумя фильмами (id просмотренный и id кандидата) -> float

            score = (0.7 * sim_struct + 0.3 * sim_text) * nr * rec  # общий вклад кандидата: гибридное весовое смешение (70% фичи, 30% текст)
            scores[cid] += score  # сумма вкладов кандидата: каждый просмотренный фильм голосует за кандидата

            reasons[cid].append({  # детали кандидата: от какого просмотренного фильма пришёл вклад, какие значения сходства, и воздействие рейтинга и свежести
                "from_film": film.title,
                "similarity_features": round(sim_struct, 3),
                "similarity_text": round(sim_text, 3),
                "rating_influence": round(nr, 3),
                "recency_influence": round(rec, 3),
            })

    if scores:
        max_score = max(scores.values())  # нормализация итоговых баллов, наибольшее значение = 1.0, остальные - процент от наибольшего значения
        for k in scores:
            scores[k] = scores[k] / max_score

    result = sorted(scores.items(), key=lambda x: x[1], reverse=True)  # итог: список кортежей, cортируем пары (movie_id, score) по убыванию score

    return [   # возвращаем список словарей
        {
            "movie_id": mid,  # id фильма-рекомендации
            "score": score,  # нормализованный score (вес) фильма-рекомендации
            "reasons": reasons[mid]   # объяснения, почему этот фильм
        }
        for mid, score in result
    ]
