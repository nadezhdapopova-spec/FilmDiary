import math
from collections import defaultdict
from datetime import date, datetime
from heapq import nlargest
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from services.tmdb import Tmdb
from services.tmdb_film import TmdbFilm

FEATURE_WEIGHTS = getattr(
    settings,
    "RECOMMENDER_FEATURE_WEIGHTS",
    {
        "director": 3.0,
        "actor": 2.0,
        "genre": 1.5,
        "keyword": 1.0,
    },
)

W_STRUCT: float = getattr(settings, "RECOMMENDER_WEIGHT_STRUCT", 0.7)
W_TEXT: float = getattr(settings, "RECOMMENDER_WEIGHT_TEXT", 0.3)
TFIDF_MAX_FEATURES: int = getattr(settings, "RECOMMENDER_TFIDF_MAX_FEATURES", 5000)
RATING_MIN: int = getattr(settings, "RECOMMENDER_RATING_MIN", 1)
RATING_MAX: int = getattr(settings, "RECOMMENDER_RATING_MAX", 10)

GENRE_PROFILE_WEIGHT: float = getattr(settings, "RECOMMENDER_GENRE_PROFILE_WEIGHT", 0.25)
GENRE_SIM_WEIGHT: float = getattr(settings, "RECOMMENDER_GENRE_SIMILARITY_WEIGHT", 0.2)
GENRE_BOOST_STRATEGY: str = getattr(settings, "RECOMMENDER_GENRE_BOOST_STRATEGY", "max")  # "max"|"mean"|"sum"

W_API_GENRE_PRIOR: float = getattr(settings, "RECOMMENDER_API_GENRE_PRIOR_WEIGHT", 0.1)
W_API_SIMILAR: float = getattr(settings, "RECOMMENDER_API_SIMILAR_WEIGHT", 0.15)
W_API_RECOMMENDED: float = getattr(settings, "RECOMMENDER_API_RECOMMENDED_WEIGHT", 0.2)

RATING_SOFTNESS: float = getattr(settings, "RECOMMENDER_RATING_SOFTNESS", 0.5)
RECENCY_SOFTNESS: float = getattr(settings, "RECOMMENDER_RECENCY_SOFTNESS", 0.5)

TOP_K_BASE: int = getattr(settings, "RECOMMENDER_TOP_K_BASE", 200)

_FEATURE_WEIGHT_CACHE: Dict[str, float] = {}  # Быстрый кэш весов по полному feature ("genre:Drama")
_FEATURE_TYPE_WEIGHT_CACHE: Dict[str, float] = {}  # Быстрый кэш весов по типу ("genre")


def fast_feature_weight(feature: str) -> float:
    """
    Возвращает вес признака вес признака по его типу ("genre:sci-fi", "actor:tom hardy"),
    с кэшированием для скорости
    """
    if not feature:
        return 1.0
    if feature in _FEATURE_WEIGHT_CACHE:  # если уже считали полный ключ — вернуть
        return _FEATURE_WEIGHT_CACHE[feature]

    ftype = feature.split(":", 1)[0]  # извлекаем тип (до первого ':')

    w = _FEATURE_TYPE_WEIGHT_CACHE.get(ftype)  # извлекаем кэш по типу
    if w is None:
        w = FEATURE_WEIGHTS.get(ftype, 1.0)
        _FEATURE_TYPE_WEIGHT_CACHE[ftype] = w  # или кэшириуем по типу

    _FEATURE_WEIGHT_CACHE[feature] = w  # или кэшируем полный ключ
    return w


def normalize_rating(rating: float) -> float:
    """Нормализует пользовательский рейтинг фильма в диапазон [0,1]"""
    r_min, r_max = float(RATING_MIN), float(RATING_MAX)
    rating = max(r_min, min(r_max, float(rating)))
    if r_max == r_min:
        return 0.0
    return (rating - r_min) / (r_max - r_min)


def recency_boost(date_watched: Optional[date]) -> float:
    """
    Логарифмически убывающий вес для свежести фильма [0..1].Даёт больший вес недавно просмотренным фильмам,
    плавно уменьшая вклад по мере старения отзыва. Логарифм делает спад медленным
    """
    if not date_watched:
        return 1.0
    days = (datetime.now().date() - date_watched).days
    days = max(0, days)
    return 1.0 / (1.0 + math.log1p(days))


def final_rating_factor(nr: float) -> float:
    """
    Плавная шкала для нормализованного рейтинга, чтобы низкий nr не занулял вклад:
    сглаживает влияние нулевых/низких значений, чтобы отзыв с низкой оценкой не давал строго ноль
    """
    alpha = RATING_SOFTNESS
    return alpha + (1.0 - alpha) * nr  # если nr=0 => alpha; nr=1 => 1


def final_recency_factor(rec: float) -> float:
    """Плавная шкала для recency:
    сглаживает влияние нулевых/низких значений, чтобы старый отзыв не давал строго ноль
    """
    beta = RECENCY_SOFTNESS
    return beta + (1.0 - beta) * rec  # если rec small -> beta минимальный вклад


class FeatureCache:
    """Кэширование признаков фильмов, чтобы не вычислять заново"""

    def __init__(self):
        self.features_map: Dict[int, Tuple[str, ...]] = (
            {}
        )  # словарь {123: ("actor:tom hardi": None, "director:nolan": None), ...}
        self.genres_map: Dict[int, Set[str]] = {}  # словарь {123: ("genre:sci-fi": None, "genre:triller": None), ...}

    def prepare_film(self, film: TmdbFilm) -> None:
        """Собирает и кэширует признаки для одного movie ("genre:action", "actor:leonardo dicaprio")"""
        if film.tmdb_id in self.features_map:
            return

        feats: List[str] = []  # список признаков фильма
        for g in film.genres:
            feats.append(f"genre:{g.lower()}")

        for a in film.actors:
            feats.append(f"actor:{a.lower()}")

        if film.director:
            feats.append(f"director:{film.director.lower()}")

        feats_tuple = tuple(dict.fromkeys(feats))  # remove duplicates, keep order
        self.features_map[film.tmdb_id] = feats_tuple
        self.genres_map[film.tmdb_id] = {f for f in feats_tuple if f.startswith("genre:")}

    def get_features(self, tmdb_id: int) -> Tuple[str, ...]:
        """
        Возвращает признаки(кортеж строк признаков) фильма из кэша, если нет - вычисляет заново
        ("actor:leonardo dicaprio", "director:christopher nolan")
        """
        return self.features_map.get(tmdb_id, ())

    def get_genres_by_id(self, tmdb_id: int) -> Set[str]:
        """Возвращает жанры(множество жанров) фильма из кэша по id фильма"""
        return self.genres_map.get(tmdb_id, set())


class FilmIndex:
    """
    Обратный индекс: feature -> set(film_ids).
    Находит все фильмы, которые имеют хотя бы один заданный признак, не перебирая весь каталог:
    сопоставляет каждый признак (feature) со множеством идентификаторов фильмов, которые содержат этот признак
    """

    def __init__(self) -> None:
        self.index: Dict[str, Set[int]] = defaultdict(set)

    def add_film(self, film_id: int, features: Iterable[str]) -> None:
        """
        Фильмы:
        film 1: feature_set = {"genre:Sci-Fi", "actor:Tom Hardy", "director:Nolan"}
        film 2: feature_set = {"genre:Drama", "actor:DiCaprio", "director:Nolan"}
        film 3: feature_set = {"genre:Sci-Fi", "actor:DiCaprio", "director:Somebody"}
        film 4: feature_set = {"genre:Comedy", "actor:Someone", "director:SomeoneElse"}
        Просмотрен film 1 ->
        self.index = {"genre:Sci-Fi": {1, 3}, "actor:Tom Hardy": {1},
                      "director:Nolan": {1, 2}, "genre:Drama": {2},
                      "actor:DiCaprio": {2,3}, "genre:Comedy": {4},...}
        """
        for f in features:
            self.index[f].add(film_id)

    def candidates_for(self, features: Iterable[str]) -> Set[int]:
        """
        Возвращает set кандидатов, которые совпадают хотя бы по одному признаку.
        Оператор |= (in-place union) добавляет все id из self.index[f] в cand:
        {1,2,3}
        """
        if not features:
            return set()
        cand = set()
        for f in features:
            cand |= self.index.get(f, set())
        return cand


class TextSimilarity:
    """Вычисляет косинусное сходство между текстами с использованием TF-IDF"""

    def __init__(self, films: List[TmdbFilm]) -> None:
        """
        Инициализация атрибутов класса:
        films — список фильмов Tmdb;
        texts — список кортежей для каждого фильма(id, описание, ключевой тэг).
        Готовит TF‑IDF‑матрицу по описаниям фильмов и маппинг tmdb_id -> индекс строки.
        Создаёт: self.matrix — sparse tf-idf матрицу документов, self.id_to_idx — словарь от id фильма к номеру строки
        """
        texts: List[str] = []
        self.id_to_idx: Dict[int, int] = {}  # нелинейный поиск, быстрее, моментально находит позиции в матрице
        for idx, film in enumerate(films):
            text = (film.overview + " " + film.tagline).strip() or " "
            texts.append(text)
            self.id_to_idx[film.tmdb_id] = idx  # матрица веса слов в текстах

        self.vectorizer = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES)
        if all(not t.strip() for t in texts):
            self.matrix = None
        else:
            self.matrix = self.vectorizer.fit_transform(texts)

    def similarity(self, id_a: int, id_b: int) -> float:
        """
        Вычисляет косинусное сходство между двумя текстами: id_a, id_b — tmdb_id фильмов.
        Возвращает: float в [0,1], где 1 = тексты одинаковы.
        """
        if self.matrix is None:
            return 0.0
        idx_a = self.id_to_idx.get(id_a)  # индексная позиция конкретного текста
        idx_b = self.id_to_idx.get(id_b)
        if idx_a is None or idx_b is None:
            return 0.0

        return float(
            cosine_similarity(self.matrix[idx_a], self.matrix[idx_b])[0, 0]
        )  # косинусное сходство между двумя текстами


def top_k_candidates_by_feature_weight(user_features: Iterable[str], inv: FilmIndex, k: int = TOP_K_BASE) -> Set[int]:
    """
    user_features: признаки исходного фильма.
    inv: FilmIndex: уже построенный обратный индекс.
    k: int: сколько лучших кандидатов взять (по умолчанию TOP_K_BASE).
    Возвращает top-K кандидатов на основе суммы весов совпавших признаков:
    - для каждого признака f берётся вес weight_f = fast_feature_weight(f);
    - для всех фильмов f_id из inv.index[f] прибавляется weight_f к их суммарному весу;
    - берутся k фильмов с максимальным суммарным весом (через nlargest)
    """
    if not user_features:
        return set()

    candidate_weights: Dict[int, float] = defaultdict(
        float
    )  # dict, где ключ - id фильма, значение - общий вес по критериям

    for f in user_features:  # для каждого признака фильма пользователя
        weight_f = fast_feature_weight(f)  # достаем вес признака фильма из кэша
        for f_id in inv.index.get(
            f, ()
        ):  # берем из словаря inv.index = {"genre:Sci-Fi": {1, 3}, "actor:Tom Hardy": {1},...} id фильма из f признака
            candidate_weights[f_id] += weight_f  # в словаре candidate_weights к фильму по id прибавляем вес

    if not candidate_weights:
        return set()

    if len(candidate_weights) <= k:  # если длина candidate_weights < k, возвращаем все id фильмов
        return set(candidate_weights.keys())

    return {
        f_id for f_id, _ in nlargest(k, candidate_weights.items(), key=lambda x: x[1])
    }  # иначе возвращаем множество id фильмов в количестве k с наибольшим весом


def build_user_genre_profile(user_reviews, feature_cache: FeatureCache) -> Dict[str, float]:
    """
    Строит профиль предпочтений жанров пользователя: какие жанры ему нравятся и насколько:
    user_reviews: queryset/список отзывов пользователя.
    Возвращает: dict[str, float], где ключ — genre, значение — нормированная «важность» жанра в [0,1].
    Если профиль пуст — возвращает {}
    """
    profile = defaultdict(float)  # жанр: вес жанра

    for review in user_reviews:  # на основе отзывов пользователя
        nr = normalize_rating(review.user_rating)
        for g in feature_cache.get_genres_by_id(review.film.tmdb_id):
            profile[g] += nr

    if not profile:
        return {}
    max_val = max(profile.values())
    return {k: v / max_val for k, v in profile.items()}


def get_tmdb_genre_map(api_client: Tmdb) -> Dict[str, int]:
    """Возвращает словарь 'genre name lower': tmdb_genre_id"""
    try:
        genres_payload = (
            api_client.get_genres()
        )  # genres = {'genres': [{'id': 28, 'name': 'боевик'}, {'id': 12, 'name': 'приключения'},]} или list
        items = []
        if isinstance(genres_payload, dict) and "genres" in genres_payload:
            items = genres_payload["genres"]
        elif isinstance(genres_payload, list):
            items = genres_payload
        tmdb_genre_id: Dict[str, int] = {}
        for g in items:
            name = g.get("name") if isinstance(g, dict) else str(g)
            g_id = g.get("id") if isinstance(g, dict) else None
            if g_id:
                tmdb_genre_id[name.strip().lower()] = g_id
        return tmdb_genre_id
    except Exception:
        return {}


def api_genre_candidates(user_genre_profile: Dict[str, float], api: Tmdb, limit: int = 300) -> Set[int]:
    """
    Возвращает tmdb_id кандидатов из внешнего API TMDB по топ-3-жанрам пользователя:
    user_genre_profile: жанровый профиль пользователя;
    limit: int: ограничение по количеству кандидатов
    """
    if not user_genre_profile or api is None:
        return set()
    result: Set[int] = set()
    genre_map = get_tmdb_genre_map(api)
    top_genres = sorted(user_genre_profile.items(), key=lambda x: x[1], reverse=True)[:3]  # топ-3 любимых жанра

    for genre_key, _ in top_genres:
        _, g_name = genre_key.split(":", 1)
        genre_name = g_name.strip().lower()
        g_id = genre_map.get(genre_name)
        if not g_id:
            continue
        try:
            movies = api.get_movies_by_genre(g_id) or []
            if isinstance(movies, dict) and "results" in movies:
                movies = movies["results"]
            for m in movies:
                tmdb_id = getattr(m, "tmdb_id", None)
                if tmdb_id:
                    result.add(tmdb_id)
                if len(result) >= limit:
                    return result
        except Exception:
            continue
    return result


def weighted_jaccard_by_features(feats_a: Iterable[str], feats_b: Iterable[str]) -> float:
    """
    Принимает множество признаков feats_a(фильм_А) и feats_a(фильм_B), каждый признак — строка типа 'actor:Tom Hardy'.
    Возвращает взвешенный Jaccard (суммарный вес общих признаков делённый на суммарный вес всех признаков) - от 0 до 1,
    где 1- одинаковые признаки
    """
    sa, sb = set(feats_a), set(feats_b)
    if not feats_a or not feats_b:
        return 0.0

    union = sa | sb  # уникальные признаки
    if not union:
        return 0.0
    inter = sa & sb

    inter_w = sum(fast_feature_weight(f) for f in inter)  # сумма весов всех пересечений
    union_w = sum(fast_feature_weight(f) for f in union)  # сумма весов всех уникальных признаков

    return inter_w / union_w if union_w else 0.0


def genre_similarity(feats_a: Iterable[str], feats_b: Iterable[str]) -> float:
    """Простое Jaccard-сходство только по жанрам, возвращает Jaccard от 0 до 1, где 1- одинаковые признаки"""
    ga = {f for f in feats_a if f.startswith("genre:")}
    gb = {f for f in feats_b if f.startswith("genre:")}
    if not ga or not gb:
        return 0.0
    inter = ga & gb
    union = ga | gb
    return len(inter) / len(union) if union else 0.0


def compute_genre_boost_for_candidate(user_genre_profile: Dict[str, float], candidate_genres: Iterable[str]) -> float:
    """
    Дополнительный буст кандидата в зависимости от того, насколько его жанры совпадают с профилем пользователя.
    user_genre_profile: жанровый профиль пользователя;
    candidate_genres: множество жанров фильма-кандидата (получено в feature_cache.get_genres_by_id(c_id)).
    Возвращает вес по профилю жанров пользователя в зависимости от стратегии:
      - "max": берём максимальную релевантность жанра среди жанров кандидата
      - "mean": берём среднее значение релевантности жанров кандидата
      - "sum": суммируем (может давать большие значения)
    """
    if not user_genre_profile or not candidate_genres:
        return 0.0
    vals = [user_genre_profile.get(g, 0.0) for g in candidate_genres]
    if not vals:
        return 0.0
    if GENRE_BOOST_STRATEGY == "mean":
        return sum(vals) / len(vals)
    if GENRE_BOOST_STRATEGY == "sum":
        return sum(vals)
    return max(vals)  # default: max


def build_recommendations(user, api: Tmdb) -> List[Dict]:
    """
    Основной алгоритм рекомендаций, формирует персональные рекомендации для user на основе:
    - признаков просмотренных фильмов (genre / actor / director / keywords и т.д.),
    - текстового сходства (TF-IDF по overview/tagline),
    - нормализованных оценок пользователя,
    - свежести оценок (recency boost),
    - explainability (почему рекомендация получена).
    Функция возвращает отсортированный список словарей рекомендаций
    с movie_id, нормализованным score и списком вкладов/объяснений:
    [{"movie_id": id, "score": 0..1, "reasons": [...]},...]
    """
    user_reviews = list(
        user.reviews.select_related("film")
    )  # получаем ревью один раз, чтобы не делать много SQL-запросов
    watched = {r.film.tmdb_id for r in user_reviews}

    films = api.get_candidate_pool()

    feature_cache = FeatureCache()  # создаётся экземпляр кэша признаков, хранит в памяти movie_id -> feature_set,
    # чтобы не пересчитывать признаки для одного фильма многократно
    inv = FilmIndex()  # создает инвертированный индекс (feature → множество movie_id)

    for film in films:
        feature_cache.prepare_film(film)
        inv.add_film(film.tmdb_id, feature_cache.get_features(film.tmdb_id))

    textsim = TextSimilarity(films)

    user_genre_profile = build_user_genre_profile(
        user_reviews, feature_cache
    )  # формируем профиль любимых жанров пользователя

    scores: Dict[int, float] = defaultdict(float)  # movie_id: накопленный вес фильма (score)
    reasons: Dict[int, List[Dict]] = defaultdict(
        list
    )  # movie_id: id фильма и объяснение, почему рекомендует его по вкладу

    for review in user_reviews:  # цикл по всем просмотренным фильмам
        src_id = review.film.tmdb_id
        src_feats = feature_cache.get_features(src_id)

        nr = final_rating_factor(normalize_rating(review.user_rating))
        rec = final_recency_factor(recency_boost(review.updated_at.date()))
        weight = nr * rec

        candidates = set()

        candidates |= top_k_candidates_by_feature_weight(src_feats, inv)
        candidates |= api_genre_candidates(user_genre_profile, api)

        candidates -= watched

        for c_id in candidates:
            sim_struct = weighted_jaccard_by_features(src_feats, feature_cache.get_features(c_id))
            sim_text = textsim.similarity(src_id, c_id)
            s_genre = genre_similarity(src_feats, feature_cache.get_features(c_id))

            boost = compute_genre_boost_for_candidate(user_genre_profile, feature_cache.get_genres_by_id(c_id))

            score = (
                W_STRUCT * sim_struct + W_TEXT * sim_text + GENRE_SIM_WEIGHT * s_genre + GENRE_PROFILE_WEIGHT * boost
            ) * weight

            scores[c_id] += score
            reasons[c_id].append(
                {
                    "from": review.film.title,
                    "sim_struct": round(sim_struct, 3),
                    "sim_text": round(sim_text, 3),
                    "genre": round(s_genre, 3),
                }
            )

    if (
        not scores
    ):  # нормализация итоговых баллов, наибольшее значение = 1.0, остальные - процент от наибольшего значения
        return []
    max_s = max(scores.values())
    for k in scores:
        scores[k] /= max_s  # теперь max(score) = 1.0

    return sorted(  # возвращаем список словарей
        [
            {
                "tmdb_id": k,  # id фильма-рекомендации
                "score": v,  # нормализованный score (вес) фильма-рекомендации
                "reasons": reasons[k],  # объяснения, почему этот фильм
            }
            for k, v in scores.items()
        ],
        key=lambda x: x["score"],
        reverse=True,
    )
