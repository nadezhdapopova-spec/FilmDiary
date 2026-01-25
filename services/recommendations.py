import math
from collections import defaultdict
from datetime import date, datetime
from heapq import nlargest
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from services.tmdb import Tmdb

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
    """Возвращает вес признака по типу. Кэширует результат для скорости"""
    if not feature:
        return 1.0
    if feature in _FEATURE_WEIGHT_CACHE:  # если уже считали полный ключ — вернуть
        return _FEATURE_WEIGHT_CACHE[feature]

    ftype = feature.split(":", 1)[0]  # извлекаем тип (до первого ':')

    if ftype in _FEATURE_TYPE_WEIGHT_CACHE:  # кэш по типу
        w = _FEATURE_TYPE_WEIGHT_CACHE[ftype]  # извлекаем кэш по типу
    else:
        w = FEATURE_WEIGHTS.get(ftype, 1.0)
        _FEATURE_TYPE_WEIGHT_CACHE[ftype] = w  # или кэшириуем по типу

    _FEATURE_WEIGHT_CACHE[feature] = w  # или кэшируем полный ключ
    return w


def normalize_rating(rating: float) -> float:
    """Нормализует пользовательский рейтинг филма r в [0,1]"""
    r_min, r_max = float(RATING_MIN), float(RATING_MAX)
    rating = max(r_min, min(r_max, float(rating)))
    if r_max == r_min:
        return 0.0
    return (rating - r_min) / (r_max - r_min)


def recency_boost(date_watched: Optional[date]) -> float:
    """Логарифмически убывающий вес для свежести фильма [0..1]."""
    if not date_watched:
        return 1.0
    days = (datetime.now().date() - date_watched).days
    days = max(0, days)
    return 1.0 / (1.0 + math.log1p(days))


def final_rating_factor(nr: float) -> float:
    """Плавная шкала для нормализованного рейтинга, чтобы низкий nr не занулял вклад"""
    alpha = RATING_SOFTNESS
    return alpha + (1.0 - alpha) * nr  # если nr=0 => alpha; nr=1 => 1


def final_recency_factor(rec: float) -> float:
    """Плавная шкала для recency"""
    beta = RECENCY_SOFTNESS
    return beta + (1.0 - beta) * rec  # если rec small -> beta минимальный вклад


class FeatureCache:
    """Кэширование признаков фильмов, чтобы не вычислять заново (ключи — локальные id)"""

    def __init__(self):
        self.features_map: Dict[int, Tuple[str, ...]] = (
            {}
        )  # словарь {123: ("actor:tom hardi": None, "director:nolan": None), ...}
        self.genres_map: Dict[int, Set[str]] = {}  # словарь {123: ("genre:sci-fi": None, "genre:triller": None), ...}

    def prepare_film(self, film) -> None:
        """Собирает и кэширует признаки для одного movie"""
        f_id = getattr(film, "id")
        if f_id in self.features_map:
            return

        feats: List[str] = []  # список признаков фильма
        for g in getattr(film, "genres", []) or []:
            name = getattr(g, "name", str(g))
            feats.append(f"genre:{name.strip().lower()}")  # добавляем в feats жанры фильма

        for a in getattr(film, "actors", []) or []:
            name = getattr(a, "name", str(a))
            feats.append(f"actor:{name.strip().lower()}")  # добавляем в feats актеров фильма

        d = getattr(film, "director", None)
        if d:
            if isinstance(d, (list, tuple, set)):  # добавляем в feats режиссера
                for dd in d:
                    feats.append(f"director:{getattr(dd, 'name', str(dd)).strip().lower()}")
            else:
                feats.append(f"director:{getattr(d, 'name', str(d)).strip().lower()}")

        feats_tuple = tuple(dict.fromkeys(feats))  # remove duplicates, keep order
        self.features_map[f_id] = feats_tuple
        self.genres_map[f_id] = {f for f in feats_tuple if f.startswith("genre:")}

    def get_features(self, film) -> Tuple[str, ...]:
        """Возвращает признаки фильма из кэша, если нет - вычисляет заново"""
        f_id = getattr(film, "id")
        if f_id not in self.features_map:
            self.prepare_film(film)
        return self.features_map.get(f_id, ())

    def get_features_by_id(self, f_id: int) -> Tuple[str, ...]:
        """Возвращает признаки фильма из кэша по id фильма"""
        return self.features_map.get(f_id, ())

    def get_genres_by_id(self, f_id: int) -> Set[str]:
        """Возвращает жанры фильма из кэша по id фильма"""
        return self.genres_map.get(f_id, set())


class FilmIndex:
    """
    Обратный индекс: feature -> set(local_film_ids).
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
        if not features:
            return
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

    def __init__(self, films: List) -> None:
        """
        Инициализация атрибутов класса:
        movies — список фильмов ORM
        texts — список кортежей для каждого фильма(id, описание, ключевой тэг)
        """
        texts: List[str] = []
        self.id_to_idx: Dict[int, int] = {}  # нелинейный поиск, быстрее, моментально находит позиции в матрице
        for idx, film in enumerate(films):
            f_id = getattr(film, "id")
            ov = getattr(film, "overview", "") or ""
            tg = getattr(film, "tagline", "") or ""
            txt = (ov + " " + tg).strip() or " "
            texts.append(txt)
            self.id_to_idx[f_id] = idx  # матрица веса слов в текстах

        if all(not t.strip() for t in texts):
            self.matrix = None
        else:
            self.vectorizer = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES)
            try:
                self.matrix = self.vectorizer.fit_transform(texts)
            except ValueError:
                self.matrix = None

    def similarity(self, id_a: int, id_b: int) -> float:
        """Вычисляет косинусное сходство между двумя текстами"""
        if self.matrix is None:
            return 0.0
        idx_a = self.id_to_idx.get(id_a)  # индексная позиция конкретного текста
        idx_b = self.id_to_idx.get(id_b)
        if idx_a is None or idx_b is None:
            return 0.0

        v1 = self.matrix[idx_a]  # матрица веса слов конкретного текста по индексной позиции
        v2 = self.matrix[idx_b]

        if v1.nnz == 0 or v2.nnz == 0:
            return 0.0  # если тексты пустые

        return float(cosine_similarity(v1, v2)[0, 0])  # косинусное сходство между двумя текстами


def top_k_candidates_by_feature_weight(user_features: Iterable[str], inv: FilmIndex, k: int = TOP_K_BASE) -> Set[int]:
    """
    Возвращает top-K кандидатов на основе суммы весов совпавших признаков
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
        ):  # берем из словаря self.index = {"genre:Sci-Fi": {1, 3}, "actor:Tom Hardy": {1},...} по очереди id фильма из f признака
            candidate_weights[f_id] += weight_f  # в словаре candidate_weights к фильму по id прибавляем вес

    if not candidate_weights:
        return set()

    if len(candidate_weights) <= k:  # если длина candidate_weights < k, возвращаем все id фильмов
        return set(candidate_weights.keys())

    return {
        f_id for f_id, _ in nlargest(k, candidate_weights.items(), key=lambda x: x[1])
    }  # иначе возвращаем множество id фильмов в количестве k с наибольшим весом


def build_user_genre_profile(
    user, feature_cache: FeatureCache, user_reviews: Optional[List] = None
) -> Dict[str, float]:
    """Строит профиль предпочтений жанров пользователя"""
    if user_reviews is None:
        user_reviews = list(user.reviews.all())
    profile: Dict[str, float] = defaultdict(float)  # жанр: вес жанра

    for review in user_reviews:  # на основе отзывов пользователя
        film = review.film
        f_id = getattr(film, "id")
        feats = feature_cache.get_features_by_id(f_id)
        if not feats:
            continue

        nr = normalize_rating(review.user_rating)
        created = getattr(review, "created_at", None)
        rec = recency_boost(created.date() if created else None)

        for genre in feats:
            if genre.startswith("genre:"):
                profile[genre] += nr * rec  # добавляет жанр: вес (с учетом нормализации веса и свежести фильма)

    if not profile:
        return {}
    max_val = max(profile.values())
    if max_val > 0:
        return {
            g: v / max_val for g, v in profile.items()
        }  # нормализация [0..1], процент относительно максимального веса жанра
    return dict(profile)


def get_tmdb_genre_map(api_client: Tmdb) -> Dict[str, int]:
    """Возвращает словарь 'genre name lower': tmdb_genre_id. Кешировать при необходимости"""
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


def api_genre_candidates(
    user_genre_profile: Dict[str, float], api: Tmdb, local_by_tmdb: Dict[int, int], limit: int = 300
) -> Set[int]:
    """Возвращает локальные ids кандидатов, полученные из TMDB по топ-3 жанрам пользователя"""
    if not user_genre_profile or api is None:
        return set()
    result: Set[int] = set()
    genre_map = get_tmdb_genre_map(api)
    top_genres = sorted(user_genre_profile.items(), key=lambda x: x[1], reverse=True)[:3]  # топ-3 любимых жанра

    for genre_key, _ in top_genres:
        _, g_name = genre_key.split(":", 1)
        genre_name = g_name.strip().lower()
        g_id = genre_map.get(genre_name.strip().lower())
        if not g_id:
            continue
        try:
            movies = api.get_movies_by_genre(g_id) or []
            if isinstance(movies, dict) and "results" in movies:
                movies = movies["results"]
            for m in movies:
                tmdb_id = getattr(m, "tmdb_id", None)
                if tmdb_id and tmdb_id in local_by_tmdb:
                    result.add(local_by_tmdb[tmdb_id])
            if len(result) >= limit:
                break
        except Exception:
            continue
    return result


def weighted_jaccard_by_features(feats_a: Iterable[str], feats_b: Iterable[str]) -> float:
    """
    Принимает множество признаков feats_a(фильм_А) и feats_a(фильм_B), каждый признак — строка типа 'actor:Tom Hardy'.
    Возвращает взвешенный Jaccard (суммарный вес общих признаков делённый на суммарный вес всех признаков)
    """
    if not feats_a or not feats_b:
        return 0.0

    sa, sb = set(feats_a), set(feats_b)

    union = sa | sb  # уникальные признаки
    if not union:
        return 0.0

    inter_w = sum(fast_feature_weight(f) for f in sa if f in sb)  # сумма весов всех пересечений
    union_w = sum(fast_feature_weight(f) for f in union)  # сумма весов всех уникальных признаков

    return inter_w / union_w if union_w else 0.0


def genre_similarity(feats_a: Iterable[str], feats_b: Iterable[str]) -> float:
    """Простое Jaccard-сходство только по жанрам"""
    ga = {f for f in feats_a if f.startswith("genre:")}
    gb = {f for f in feats_b if f.startswith("genre:")}
    if not ga or not gb:
        return 0.0
    inter = ga & gb
    union = ga | gb
    return len(inter) / len(union) if union else 0.0


def compute_genre_boost_for_candidate(user_genre_profile: Dict[str, float], candidate_genres: Iterable[str]) -> float:
    """
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
    strat = GENRE_BOOST_STRATEGY
    if strat == "mean":
        return sum(vals) / len(vals)
    if strat == "sum":
        return sum(vals)
    return max(vals)  # default: max


def build_recommendations(
    user, all_films: List, api_client: Optional[Tmdb] = None, top_k_base: int = TOP_K_BASE
) -> List[Dict]:
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
    feature_cache = FeatureCache()  # создаётся экземпляр кэша признаков, хранит в памяти movie_id -> feature_set,
    # чтобы не пересчитывать признаки для одного фильма многократно
    film_by_local: Dict[int, object] = {}  # доступ к объектам фильмов создается сразу и один раз
    local_by_tmdb: Dict[int, int] = {}

    for film in all_films:
        l_id = getattr(film, "id")
        film_by_local[l_id] = film
        tm_id = getattr(film, "tmdb_id", None)
        if tm_id:
            local_by_tmdb[tm_id] = l_id
        feature_cache.prepare_film(film)  # собирает и кэширует признаки для каждого movie

    inv = FilmIndex()  # создает инвертированный индекс (feature → множество movie_id)
    for f_id, feats in feature_cache.features_map.items():
        inv.add_film(f_id, feats)

    textsim = TextSimilarity(all_films)  # вызван TF-IDF модуль

    user_reviews = list(user.reviews.all())  # получаем ревью один раз, чтобы не делать много SQL-запросов
    watched: Set[int] = {r.film_id for r in user_reviews}

    user_genre_profile = build_user_genre_profile(
        user, feature_cache, user_reviews
    )  # формируем профиль любимых жанров пользователя
    api_genre_prior = api_genre_candidates(user_genre_profile, api_client, local_by_tmdb) if api_client else set()
    api_genre_prior = {
        fid for fid in api_genre_prior if fid in film_by_local
    }  # фильтруем, чтобы в api_genre_prior были только локальные ids

    sim_text_cache: Dict[Tuple[int, int], float] = {}
    api_cache_similar: Dict[int, Set[int]] = {}  # множество id похожих фильмов из API TMDB
    api_cache_recommended: Dict[int, Set[int]] = {}  # множество id рекомендованных фильмов из API TMDB
    scores: Dict[int, float] = defaultdict(float)  # movie_id: накопленный вес фильма (score)
    reasons: Dict[int, List[Dict]] = defaultdict(
        list
    )  # movie_id: id фильма и объяснение, почему рекомендует его по вкладу

    for review in user_reviews:  # цикл по всем просмотренным фильмам
        film = review.film
        f_id = getattr(film, "id")
        user_feats = feature_cache.get_features_by_id(f_id)
        if not user_feats:
            continue

        nr = normalize_rating(review.user_rating)  # нормализованная оценка пользователя в диапазон [0,1]
        created = getattr(review, "created_at", None)
        if isinstance(created, datetime):
            created = created.date()
        rec = recency_boost(created)  # коэффициент свежести
        rating_factor = final_rating_factor(nr)
        recency_factor = final_recency_factor(rec)

        k = max(top_k_base, len(user_feats) * 20)
        cand_ids = top_k_candidates_by_feature_weight(
            user_feats, inv, k=k
        )  # отбор лучших кандидатов, совпадающих по признакам
        cand_ids -= watched  # исключить уже просмотренные

        cand_ids |= api_genre_prior  # быстрое объединение с кандидатами по жанру
        cand_ids -= watched

        api_similar_local: Set[int] = set()  # API похожих/рекомендованных — кэшируем локальные ids
        api_recommended_local: Set[int] = set()
        if api_client:
            tmdb_id = getattr(film, "tmdb_id", None)
            if tmdb_id:
                if tmdb_id not in api_cache_similar:
                    try:
                        sim_list = (
                            api_client.get_similar_movies(tmdb_id) or []
                        )  # множество id похожих фильмов из API TMDB
                        tmdb_ids = [getattr(m, "tmdb_id", None) for m in sim_list]
                        api_cache_similar[tmdb_id] = {local_by_tmdb[t] for t in tmdb_ids if t in local_by_tmdb}
                    except Exception:
                        api_cache_similar[tmdb_id] = set()

                if tmdb_id not in api_cache_recommended:
                    try:
                        rec_list = api_client.get_recommended_movies(tmdb_id) or []
                        tmdb_ids = [getattr(m, "tmdb_id", None) for m in rec_list]
                        api_cache_recommended[tmdb_id] = {local_by_tmdb[t] for t in tmdb_ids if t in local_by_tmdb}
                    except Exception:
                        api_cache_recommended[tmdb_id] = set()
                api_similar_local = api_cache_similar.get(tmdb_id, set())
                api_recommended_local = api_cache_recommended.get(tmdb_id, set())

        user_genres = feature_cache.get_genres_by_id(f_id)

        for c_id in cand_ids:  # для id кандидата c_id получаем сам объект candidate из movie_by_id
            candidate = film_by_local.get(c_id)
            if not candidate:
                continue
            cand_feats = feature_cache.get_features_by_id(c_id)  # feature_set для кандидата

            sim_struct = weighted_jaccard_by_features(
                user_feats, cand_feats
            )  # вес кандидата по отношению к просмотренному фильму, чем больше совпадающих (и редких/важных) признаков — тем выше sim_struct
            key = (f_id, c_id)
            sim_text = sim_text_cache.get(
                key
            )  # TF-IDF similarity из кэша: косинусное сходство между двумя фильмами (id просмотренный и id кандидата) -> float
            if sim_text is None:
                sim_text = textsim.similarity(f_id, c_id)  # иначе TF-IDF similarity вычисляется
                sim_text_cache[key] = sim_text

            base_score = (
                W_STRUCT * sim_struct + W_TEXT * sim_text
            )  # общий вклад кандидата: гибридное весовое смешение (70% фичи, 30% текст)

            genre_boost = 0.0
            if user_genre_profile:  # добавляет вес жанровых предпочтений пользователя
                genre_boost = compute_genre_boost_for_candidate(
                    user_genre_profile, feature_cache.get_genres_by_id(c_id)
                )

            g_sim = genre_similarity(user_genres, feature_cache.get_genres_by_id(c_id))  # жанровое сходство

            api_bonus = 0.0
            if c_id in api_genre_prior:
                api_bonus += W_API_GENRE_PRIOR  # c учетом веса жанра рекомендаций по жанру API TMDB
            if c_id in api_similar_local:
                api_bonus += W_API_SIMILAR  # c учетом веса жанра рекомендаций похожих фильмов API TMDB
            if c_id in api_recommended_local:
                api_bonus += W_API_RECOMMENDED  # c учетом веса жанра рекомендуемых фильмов API TMDB

            score = base_score
            score += GENRE_PROFILE_WEIGHT * genre_boost
            score += GENRE_SIM_WEIGHT * g_sim
            score += api_bonus

            final_contrib = (
                score * rating_factor * recency_factor
            )  # финальный вклад c учетом нормализации оценки и коэффициента свежести
            if final_contrib <= 0:
                continue

            scores[c_id] += final_contrib

            reasons[c_id].append(
                {  # детали кандидата: от какого просмотренного фильма пришёл вклад, какие значения сходства, и воздействие рейтинга и свежести
                    "from_film": getattr(film, "title", str(f_id)),
                    "sim_struct": round(sim_struct, 4),
                    "sim_text": round(sim_text, 4),
                    "genre_boost": round(genre_boost, 4),
                    "genre_similarity": round(g_sim, 4),
                    "api_bonus": round(api_bonus, 4),
                    "rating_factor": round(rating_factor, 3),
                    "recency_factor": round(recency_factor, 3),
                }
            )

    if scores:
        max_score = max(
            scores.values()
        )  # нормализация итоговых баллов, наибольшее значение = 1.0, остальные - процент от наибольшего значения
        if max_score > 0:
            for k in list(scores.keys()):
                scores[k] /= max_score

    result = sorted(
        scores.items(), key=lambda x: x[1], reverse=True
    )  # итог: список кортежей, cортируем пары (movie_id, score) по убыванию score

    return [  # возвращаем список словарей
        {
            "movie_id": m_id,  # id фильма-рекомендации
            "score": score,  # нормализованный score (вес) фильма-рекомендации
            "reasons": reasons[m_id],  # объяснения, почему этот фильм
        }
        for m_id, score in result
    ]
