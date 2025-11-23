import math
from collections import defaultdict
from datetime import datetime
import datetime

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from services.tmdb import Tmdb

FEATURE_WEIGHTS = getattr(settings, "RECOMMENDER_FEATURE_WEIGHTS", {})


class FeatureCache:
    """Кэширование признаков фильмов, чтобы не вычислять заново"""

    def __init__(self):
        self.cache = {}

    def get(self, movie):
        if movie.id not in self.cache:
            features = set(movie.feature_set or [])
            self.cache[movie.id] = features
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
        if not feature_set:
            return
        for f in feature_set:
            self.index[f].add(movie_id)

    def candidates_for(self, feature_set: set) -> set:
        """
        Возвращает set кандидатов, которые совпадают хотя бы по одному признаку.
        Оператор |= (in-place union) добавляет все id из self.index[f] в cand:
        {1,2,3}
        """
        if not feature_set:
            return set()
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
            (m.id, ((m.overview or "") + " " + (m.tagline or "")).strip())
            for m in movies
        ]
        self.ids = [m[0] for m in texts]
        content = [m[1] or "empty" for m in texts]

        self.vectorizer = TfidfVectorizer(max_features=getattr(settings, "RECOMMENDER_TFIDF_MAX_FEATURES", 5000))  # преобразует тексты в TF-IDF векторы
        self.matrix = self.vectorizer.fit_transform(content)  # матрица веса слов в текстах

    def similarity(self, id_a: str, id_b: str) -> float:
        """Вычисляет косинусное сходство между двумя текстами"""
        try:
            idx_a = self.ids.index(id_a)  # индексная позиция конкретного текста
            idx_b = self.ids.index(id_b)
        except ValueError:
            return 0.0

        v1 = self.matrix[idx_a]   # матрица веса слов конкретного текста по индексной позиции
        v2 = self.matrix[idx_b]

        if v1.nnz == 0 or v2.nnz == 0:
            return 0.0  # если тексты пустые

        return cosine_similarity(v1, v2)[0][0]  # косинусное сходство между двумя текстами


def feature_weight(f: str) -> float:
    """
    Принимает строку формата '<тип>:<значение>'(например 'actor:Tom Hardy'
    Возвращает вес из FEATURE_WEIGHTS по типу признака (actor/genre/director) или дефолтный(1)"""
    if not f:
        return 1
    f_type = f.split(":", 1)[0]
    return FEATURE_WEIGHTS.get(f_type, 1)


def top_k_candidates_by_feature_weight(user_features, inverted_index, k=200):
    """
    Возвращает top-K кандидатов на основе суммы весов совпавших признаков
    """
    if not user_features:
        return set()

    candidate_weights = defaultdict(float)  # dict, где ключ - id фильма, значение - общий вес по критериям

    for f in user_features:  # достаем всех кандидатов из инвертированного индекса
        weight_f = feature_weight(f)  # "actor:Tom Hardy"
        movie_ids = inverted_index.index.get(f, ())  # {13, 44, 88}

        for mid in movie_ids:  # для каждого фильма-кандидата суммируется общий вес по критериям
            candidate_weights[mid] += weight_f

    if not candidate_weights:
        return set()

    if len(candidate_weights) > k: # выделяем top-K по сумме весов
        top_candidates = sorted(  # берём только K самых больших элементов
            candidate_weights.items(),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        return {mid for mid, w in top_candidates} # set из id фильмов с наибольшим весом

    return set(candidate_weights.keys())  # set из id фильмов с наибольшим весом


def jaccard_weighted(set_a: set, set_b: set) -> float:
    """
    Принимает множество признаков set_a(фильм_А) и set_b(фильм_B), каждый признак — строка типа 'actor:Tom Hardy'.
    Возвращает взвешенный Jaccard (суммарный вес общих признаков делённый на суммарный вес всех признаков)
    """
    if not set_a or not set_b:
        return 0.0

    inter = set_a & set_b  # пересечения
    union = set_a | set_b  # уникальные признаки

    if not union:
        return 0.0

    inter_w = sum(feature_weight(f) for f in inter)  # сумма весов всех пересечений
    union_w = sum(feature_weight(f) for f in union)  # сумма весов всех уникальных признаков

    return inter_w / union_w if union_w else 0.0


def normalize_rating(rating: int) -> float:
    """Нормализация рейтинга пользователя от 1..10 -> 0..1"""
    r_min = getattr(settings, "RECOMMENDER_RATING_MIN", 1)
    r_max = getattr(settings, "RECOMMENDER_RATING_MAX", 10)

    rating = max(r_min, min(r_max, rating))
    return (rating - r_min) / (r_max - r_min)


def recency_boost(date_watched: datetime.date) -> float:
    """
    Делает вежие фильмы важнее.
    Логарифмическая декрементация: даёт умеренно-быстрое уменьшение влияния старых оценок,
    но не экспоненциальное и не слишком резкое.
    """
    if not date_watched:
        return 1.0

    days = (datetime.now().date() - date_watched).days
    days = max(0, days)
    return 1 / (1 + math.log1p(days))   # 1/(1+ln(1+days))


def build_user_genre_profile(user, feature_cache: FeatureCache) -> dict:
    """Строит профиль предпочтений жанров пользователя"""
    profile = defaultdict(float)

    for review in user.reviews.all():
        features = feature_cache.get(review.film)
        if not features:
            continue

        nr = normalize_rating(review.rating)
        rec = recency_boost(review.created_at.date())

        for f in features:
            if f.startswith("genre:"):
                profile[f] += nr * rec

    if not profile:
        return {}

    max_val = max(profile.values())
    if max_val > 0:
        for g in profile:
            profile[g] /= max_val  # нормализация [0..1], процент относительно максимального веса жанра

    return dict(profile)


def genre_similarity(features_a: set, features_b: set) -> float:
    """Простое Jaccard-сходство только по жанрам"""
    ga = {f for f in features_a if f.startswith("genre:")}
    gb = {f for f in features_b if f.startswith("genre:")}

    if not ga or not gb:
        return 0.0

    inter = ga & gb
    union = ga | gb

    return len(inter) / len(union) if union else 0.0


def api_genre_candidates(user_genre_profile: dict, api_client: Tmdb, limit: int = 300) -> set:
    """Возвращает множество кандидатов через API TMDB на основе любимых жанров"""
    result = set()

    sorted_genres = sorted(
        user_genre_profile.items(),
        key=lambda x: x[1],
        reverse=True
    )

    for genre, weight in sorted_genres[:3]:
        genre_name = genre.split(":", 1)[1]

        movies = api_client.get_movies_by_genre(genre_name)
        result.update(m.id for m in movies)

        if len(result) >= limit:
            break

    return result


def build_recommendations(user, all_movies: list, api_client=None) -> list[dict]:
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
    movie_by_id = {m.id: m for m in all_movies}  # доступ к объектам фильмов создается сразу и один раз

    inv = InvertedIndex()  # создает инвертированный индекс (feature → множество movie_id)
    for movie in all_movies:
        inv.add_movie(movie.id, feature_cache.get(movie))

    textsim = TextSimilarity(all_movies)  # вызван TF-IDF модуль

    genre_profile = build_user_genre_profile(user, feature_cache)  # формируем профиль любимых жанров пользователя
    w_profile = getattr(settings, "RECOMMENDER_GENRE_PROFILE_WEIGHT", 0.25)  # вес жанра из профиля любимых жанров пользователя = 0.25
    w_genre_sim = getattr(settings, "RECOMMENDER_GENRE_SIMILARITY_WEIGHT", 0.2)  # вес Jaccard-сходства похожих фильмов по жанрам пользователя = 0.2

    api_genre_prior = set()  # множество кандидатов через API TMDB на основе профиля любимых жанров
    if api_client and genre_profile:
        api_genre_prior = api_genre_candidates(genre_profile, api_client)

    w_api_genre = getattr(settings, "RECOMMENDER_API_GENRE_PRIOR_WEIGHT", 0.1)  # вес жанра рекомендаций по жанру API TMDB
    w_api_similar = getattr(settings, "RECOMMENDER_API_SIMILAR_WEIGHT", 0.15)  # вес жанра рекомендаций похожих фильмов API TMDB
    w_api_recommended = getattr(settings, "RECOMMENDER_API_RECOMMENDED_WEIGHT", 0.2)  # вес жанра рекомендуемых фильмов API TMDB

    scores = defaultdict(float)  # словарь movie_id -> накопленный score (float)
    reasons = defaultdict(list) # словарь movie_id -> list of dict: id фильма и объяснение, почему рекомендует его по вкладу
    w_struct = getattr(settings, "RECOMMENDER_WEIGHT_STRUCT", 0.7)
    w_text = getattr(settings, "RECOMMENDER_WEIGHT_TEXT", 0.3)

    for review in user.reviews.all():  # цикл по всем просмотренным фильмам
        film = review.film
        user_features = feature_cache.get(film)
        if not user_features:
            continue

        nr = normalize_rating(review.rating)  # нормализованная оценка пользователя в диапазон [0,1]
        rec = recency_boost(review.created_at.date()) # коэффициент свежести

        k = max(100, len(user_features) * 20)
        cand_ids = top_k_candidates_by_feature_weight(user_features, inv, k)  # отбор лучших кандидатов, совпадающих по признакам
        cand_ids -= watched  # исключить уже просмотренные

        cand_ids |= api_genre_prior
        cand_ids -= watched

        if api_client:
            api_similar = {m.id for m in api_client.get_similar_movies(film.id)}  # множество id похожих фильмов из API TMDB
            api_recommended = {m.id for m in api_client.get_recommended_movies(film.id)}  # множество id рекомендованных фильмов из API TMDB
        else:
            api_similar = api_recommended = set()

        for cid in cand_ids:  # для id кандидата cid получаем сам объект candidate из movie_by_id
            candidate = movie_by_id.get(cid)
            if not candidate:
                continue
            cand_features = feature_cache.get(candidate)  # feature_set для кандидата

            sim_struct = jaccard_weighted(user_features, cand_features) # вес кандидата по отношению к просмотренному фильму, чем больше совпадающих (и редких/важных) признаков — тем выше sim_struct
            sim_text = textsim.similarity(film.id, cid)  # TF-IDF similarity: косинусное сходство между двумя фильмами (id просмотренный и id кандидата) -> float

            score = (w_struct * sim_struct + w_text * sim_text)  # общий вклад кандидата: гибридное весовое смешение (70% фичи, 30% текст)

            if genre_profile:  # добавляет вес жанровых предпочтений пользователя
                score += w_profile * sum(
                    genre_profile.get(g, 0.0)
                    for g in cand_features if g.startswith("genre:")
                )

            g_sim = genre_similarity(user_features, cand_features)  # жанровое сходство
            score += w_genre_sim * g_sim  # c учетом веса Jaccard сходства

            if cid in api_genre_prior:
                score += w_api_genre  # c учетом веса жанра рекомендаций по жанру API TMDB

            if cid in api_similar:
                score += w_api_similar  # c учетом веса жанра рекомендаций похожих фильмов API TMDB

            if cid in api_recommended:
                score += w_api_recommended  # c учетом веса жанра рекомендуемых фильмов API TMDB

            score *= nr * rec  # c учетом нормализации оценки и коэффициента свежести
            scores[cid] += score  # финальный вклад

            reasons[cid].append({  # детали кандидата: от какого просмотренного фильма пришёл вклад, какие значения сходства, и воздействие рейтинга и свежести
                "from_film": film.title,
                "similarity_features": round(sim_struct, 3),
                "similarity_text": round(sim_text, 3),
                "rating_influence": round(nr, 3),
                "recency_influence": round(rec, 3),
            })

    if scores:
        max_score = max(scores.values())  # нормализация итоговых баллов, наибольшее значение = 1.0, остальные - процент от наибольшего значения
        if max_score > 0:
            for cid in scores:
                scores[cid] /= max_score

    result = sorted(scores.items(), key=lambda x: x[1], reverse=True)  # итог: список кортежей, cортируем пары (movie_id, score) по убыванию score

    return [   # возвращаем список словарей
        {
            "movie_id": mid,  # id фильма-рекомендации
            "score": score,  # нормализованный score (вес) фильма-рекомендации
            "reasons": reasons[mid]   # объяснения, почему этот фильм
        }
        for mid, score in result
    ]
