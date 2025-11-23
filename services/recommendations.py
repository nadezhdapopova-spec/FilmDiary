import math
from collections import defaultdict
from datetime import datetime
from heapq import nlargest
from typing import Dict, Tuple, Set, List, Iterable, Optional

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import settings
from services.tmdb import Tmdb


FEATURE_WEIGHTS = getattr(settings, "RECOMMENDER_FEATURE_WEIGHTS", {
    "director": 3.0,
    "actor": 2.0,
    "genre": 1.5,
    "keyword": 1.0,
})

W_STRUCT: float = getattr(settings, "RECOMMENDER_WEIGHT_STRUCT", 0.7)
W_TEXT: float = getattr(settings, "RECOMMENDER_WEIGHT_TEXT", 0.3)
TFIDF_MAX_FEATURES: int = getattr(settings, "RECOMMENDER_TFIDF_MAX_FEATURES", 5000)
RATING_MIN: int = getattr(settings, "RECOMMENDER_RATING_MIN", 1)
RATING_MAX: int = getattr(settings, "RECOMMENDER_RATING_MAX", 10)

W_GENRE_PROFILE: float = getattr(settings, "RECOMMENDER_GENRE_PROFILE_WEIGHT", 0.25)
W_GENRE_SIM: float = getattr(settings, "RECOMMENDER_GENRE_SIMILARITY_WEIGHT", 0.2)
W_API_GENRE_PRIOR: float = getattr(settings, "RECOMMENDER_API_GENRE_PRIOR_WEIGHT", 0.1)
W_API_SIMILAR: float = getattr(settings, "RECOMMENDER_API_SIMILAR_WEIGHT", 0.15)
W_API_RECOMMENDED: float = getattr(settings, "RECOMMENDER_API_RECOMMENDED_WEIGHT", 0.2)

_FEATURE_WEIGHT_CACHE: Dict[str, float] = {}  # Быстрый кэш весов по полному feature ("genre:Drama")
_FEATURE_TYPE_WEIGHT_CACHE: Dict[str, float] = {}  # Быстрый кэш весов по типу ("genre")


def get_local_id(film) -> int:
    """Единая точка получения локального ID ORM-модели"""
    return getattr(film, "id")


def get_tmdb_id(film) -> Optional[int]:
    """Единая точка получения TMDB ID ORM-модели"""
    return getattr(film, "tmdb_id", None)


def fast_feature_weight(feature: str) -> float:
    """Возвращает вес признака. Кэширует результат для скорости"""
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


class FeatureCache:
    """Кэширование признаков фильмов, чтобы не вычислять заново (ключи — локальные ID)"""

    def __init__(self):
        self.features_map: Dict[int, Tuple[str, ...]] = {}  # словарь {123: ("actor:tom hardi": None, "director:nolan": None), ...}
        self.genres_map: Dict[int, Set[str]] = {}  # словарь {123: ("genre:sci-fi": None, "genre:triller": None), ...}

    def prepare_film(self, film) -> None:
        """Собирает и кэширует признаки для одного movie"""
        f_id = get_local_id(film)
        if f_id in self.features_map:
            return

        feats: List[str] = [] # список признаков фильма
        for g in getattr(film, "genres", []) or []:
            name = getattr(g, "name", str(g))
            feats.append(f"genre:{name.strip().lower()}")  # добавляем в feats жанры фильма

        for a in getattr(film, "actors", []) or []:
            name = getattr(a, "name", str(a))
            feats.append(f"actor:{name.strip().lower()}")  # добавляем в feats актеров фильма

        d = getattr(film, "director", None)
        if d:
            feats.append(f"director:{getattr(d, 'name', str(d)).strip().lower()}")  # добавляем в feats режиссера

        feats_tuple = tuple(dict.fromkeys(feats))  # remove duplicates, keep order
        self.features_map[f_id] = feats_tuple
        self.genres_map[f_id] = {f for f in feats_tuple if f.startswith("genre:")}

    def get_features(self, film) -> Tuple[str, ...]:
        """Возвращает признаки фильма из кэша, если нет - вычисляет заново"""
        f_id = get_local_id(film)
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
        texts = []
        self.id_to_idx: Dict[int, int] = {}  # нелинейный поиск, быстрее, моментально находит позиции в матрице
        for idx, film in enumerate(films):
            f_id = get_local_id(film)
            ov = getattr(film, "overview", "") or ""
            tg = getattr(film, "tagline", "") or ""
            txt = (ov + " " + tg).strip() or " "
            texts.append(txt)
            self.id_to_idx[f_id] = idx  # матрица веса слов в текстах
        self.vectorizer = TfidfVectorizer(max_features=TFIDF_MAX_FEATURES)
        self.matrix = self.vectorizer.fit_transform(texts)

    def similarity(self, id_a: int, id_b: int) -> float:
        """Вычисляет косинусное сходство между двумя текстами"""
        idx_a = self.id_to_idx.get(id_a)  # индексная позиция конкретного текста
        idx_b = self.id_to_idx.get(id_b)
        if idx_a is None or idx_b is None:
            return 0.0

        v1 = self.matrix[idx_a]   # матрица веса слов конкретного текста по индексной позиции
        v2 = self.matrix[idx_b]

        if v1.nnz == 0 or v2.nnz == 0:
            return 0.0  # если тексты пустые

        return float(cosine_similarity(v1, v2)[0, 0])  # косинусное сходство между двумя текстами


def feature_weight(f: str) -> float:
    """
    Принимает строку формата '<тип>:<значение>'(например 'actor:Tom Hardy'
    Возвращает вес из FEATURE_WEIGHTS по типу признака (actor/genre/director) или дефолтный(1)"""
    if not f:
        return 1
    f_type = f.split(":", 1)[0]
    return FEATURE_WEIGHTS.get(f_type, 1)


def normalize_rating(rating: float) -> float:
    """Нормализация рейтинга пользователя от 1..10 -> 0..1"""
    rating = max(float(RATING_MIN), min(float(RATING_MAX), rating))
    if RATING_MAX == RATING_MIN:
        return 0.0
    return (rating - RATING_MIN) / (RATING_MAX - RATING_MIN)


def recency_boost(date_watched: Optional[datetime.date]) -> float:
    """
    Делает вежие фильмы важнее.
    Логарифмическая декрементация: даёт умеренно-быстрое уменьшение влияния старых оценок,
    но не экспоненциальное и не слишком резкое.
    """
    if not date_watched:
        return 1.0
    days = (datetime.now().date() - date_watched).days
    days = max(0, days)
    return 1.0 / (1.0 + math.log1p(days))   # 1/(1+ln(1+days))


def weighted_jaccard_by_features(feats_a: Iterable[str], feats_b: Iterable[str]) -> float:
    """
    Принимает множество признаков feats_a(фильм_А) и feats_a(фильм_B), каждый признак — строка типа 'actor:Tom Hardy'.
    Возвращает взвешенный Jaccard (суммарный вес общих признаков делённый на суммарный вес всех признаков)
    """
    sa, sb = set(feats_a), set(feats_b)
    if not sa or not sb:
        return 0.0

    inter = sa & sb  # пересечения
    union = sa | sb  # уникальные признаки

    if not union:
        return 0.0

    inter_w = sum(fast_feature_weight(f) for f in inter)  # сумма весов всех пересечений
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


def top_k_candidates_by_feature_weight(user_features: Iterable[str], inv: FilmIndex, k: int = 200) -> Set[int]:
    """
    Возвращает top-K кандидатов на основе суммы весов совпавших признаков
    """
    if not user_features:
        return set()

    candidate_weights: Dict[int, float] = defaultdict(float)  # dict, где ключ - id фильма, значение - общий вес по критериям

    for f in user_features:  # для каждого признака фильма пользователя
        weight_f = fast_feature_weight(f)  # достаем вес признака фильма из кэша
        for f_id in inv.index.get(f, ()):  # берем из словаря self.index = {"genre:Sci-Fi": {1, 3}, "actor:Tom Hardy": {1},...} по очереди id фильма из f признака
            candidate_weights[f_id] += weight_f  # в словаре candidate_weights к фильму по id прибавляем вес

    if not candidate_weights:
        return set()

    if len(candidate_weights) <= k:  # если длина candidate_weights < k, возвращаем все id фильмов
        return set(candidate_weights.keys())

    top = nlargest(k, candidate_weights.items(), key=lambda x: x[1])
    return {f_id for f_id, _ in top} # иначе возвращаем множество id фильмов в количестве k с наибольшим весом


def build_user_genre_profile(user, feature_cache: FeatureCache) -> Dict[str, float]:
    """Строит профиль предпочтений жанров пользователя"""
    profile: Dict[str, float] = defaultdict(float)  # жанр: вес жанра

    for review in user.reviews.all():  # на основе отзывов пользователя
        film = review.film
        feats = feature_cache.get_features(film)
        if not feats:
            continue

        nr = normalize_rating(review.rating)
        rec = recency_boost(getattr(review, "created_at", None).date() if getattr(review, "created_at", None) else None)

        for genre in feats:
            if genre.startswith("genre:"):
                profile[genre] += nr * rec  # добавляет жанр: вес (с учетом нормализации веса и свежести фильма)

    if not profile:
        return {}

    max_val = max(profile.values())
    if max_val > 0:
        return {g: v / max_val for g, v in profile.items()}  # нормализация [0..1], процент относительно максимального веса жанра
    return dict(profile)


def resolve_tmdb_to_local(tmdb_ids: Iterable[int], local_by_tmdb: Dict[int, int]) -> Set[int]:
    """Преобразует список TMDB id → локальные ORM id"""
    return {local_by_tmdb[t] for t in tmdb_ids if t in local_by_tmdb}


def api_genre_candidates(user_genre_profile: Dict[str, float], api: Tmdb, local_by_tmdb: Dict[int, int], limit: int = 300) -> Set[int]:
    """Возвращает множество кандидатов через API TMDB на основе любимых жанров"""
    if not user_genre_profile:
        return set()
    result: Set[int] = set()
    top_genres = sorted(user_genre_profile.items(), key=lambda x: x[1], reverse=True)[:3]  # топ-3 любимых жанра

    for genre, _ in top_genres:
        _, genre_name = genre.split(":", 1)
        try:
            movies = api.get_movies_by_genre(genre_name)
            tmdb_ids = [m.tmdb_id for m in movies]
            result |= resolve_tmdb_to_local(tmdb_ids, local_by_tmdb)

        except Exception:
            continue
        if len(result) >= limit:
            break

    return result


def build_recommendations(user, all_films: List, api_client: Optional[Tmdb] = None, top_k_base: int = 200) -> List[Dict]:
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
        f_id = get_local_id(film)
        tm_id = get_tmdb_id(film)

        film_by_local[f_id] = film
        if tm_id:
            local_by_tmdb[tm_id] = f_id

        feature_cache.prepare_film(film)  # собирает и кэширует признаки для каждого movie
    watched: Set[int] = {r.film_id for r in user.reviews.all()}  # собирает id просмотренных фильмов (watched: set)

    inv = FilmIndex()  # создает инвертированный индекс (feature → множество movie_id)
    for f_id, feats in feature_cache.features_map.items():
        inv.add_film(f_id, feats)

    textsim = TextSimilarity(all_films)  # вызван TF-IDF модуль

    user_genre_profile = build_user_genre_profile(user, feature_cache)  # формируем профиль любимых жанров пользователя
    api_genre_prior = api_genre_candidates(user_genre_profile, api_client, local_by_tmdb) if api_client else set()

    scores: Dict[int, float] = defaultdict(float)  # movie_id: накопленный вес фильма (score)
    reasons: Dict[int, List[Dict]] = defaultdict(list) # movie_id: id фильма и объяснение, почему рекомендует его по вкладу

    for review in user.reviews.all():  # цикл по всем просмотренным фильмам
        film = review.film
        user_feats = feature_cache.get_features(film)
        if not user_feats:
            continue

        api_similar: Set[int] = set()
        api_recommended: Set[int] = set()
        if api_client:
            tmdb_id = get_tmdb_id(film)
            if tmdb_id:
                try:
                    similar_movies = api_client.get_similar_movies(tmdb_id)  # множество id похожих фильмов из API TMDB
                    tmdb_ids = [m.tmdb_id for m in similar_movies]
                    api_similar = resolve_tmdb_to_local(tmdb_ids, local_by_tmdb)
                except Exception:
                    api_similar = set()

                try:
                    recs = api_client.get_recommended_movies(tmdb_id)
                    tmdb_ids = [m.tmdb_id for m in recs]
                    api_recommended = resolve_tmdb_to_local(tmdb_ids, local_by_tmdb)  # множество id рекомендованных фильмов из API TMDB
                except Exception:
                    api_recommended = set()

        nr = normalize_rating(review.rating)  # нормализованная оценка пользователя в диапазон [0,1]
        created = getattr(review, "created_at", None)
        rec = recency_boost(created.date() if created else None) # коэффициент свежести
        k = max(top_k_base, len(user_feats) * 20)
        cand_ids = top_k_candidates_by_feature_weight(user_feats, inv, k)  # отбор лучших кандидатов, совпадающих по признакам
        cand_ids -= watched  # исключить уже просмотренные

        cand_ids |= api_genre_prior  # быстрое объединение с кандидатами по жанру
        cand_ids -= watched

        for c_id in cand_ids:  # для id кандидата c_id получаем сам объект candidate из movie_by_id
            candidate = film_by_local.get(c_id)
            if not candidate:
                continue
            cand_feats = feature_cache.get_features_by_id(c_id)  # feature_set для кандидата

            sim_struct = weighted_jaccard_by_features(user_feats, cand_feats) # вес кандидата по отношению к просмотренному фильму, чем больше совпадающих (и редких/важных) признаков — тем выше sim_struct
            sim_text = textsim.similarity(film.id, c_id)  # TF-IDF similarity: косинусное сходство между двумя фильмами (id просмотренный и id кандидата) -> float

            score = (W_STRUCT * sim_struct + W_TEXT * sim_text)  # общий вклад кандидата: гибридное весовое смешение (70% фичи, 30% текст)

            if user_genre_profile:  # добавляет вес жанровых предпочтений пользователя
                genre_boost = sum(user_genre_profile.get(g, 0.0) for g in feature_cache.get_genres_by_id(c_id))
            else:
                genre_boost = 0
            score += W_GENRE_PROFILE * genre_boost

            g_sim = genre_similarity(user_feats, cand_feats)  # жанровое сходство
            score += W_GENRE_SIM * g_sim  # c учетом веса Jaccard сходства

            if c_id in api_genre_prior:
                score += W_API_GENRE_PRIOR  # c учетом веса жанра рекомендаций по жанру API TMDB
            if c_id in api_similar:
                score += W_API_SIMILAR  # c учетом веса жанра рекомендаций похожих фильмов API TMDB
            if c_id in api_recommended:
                score += W_API_RECOMMENDED  # c учетом веса жанра рекомендуемых фильмов API TMDB

            final_contrib = score * nr * rec  # финальный вклад c учетом нормализации оценки и коэффициента свежести
            if final_contrib <= 0:
                continue

            scores[c_id] += final_contrib

            reasons[c_id].append({  # детали кандидата: от какого просмотренного фильма пришёл вклад, какие значения сходства, и воздействие рейтинга и свежести
                "from_film": getattr(film, "title", str(film.id)),
                "sim_struct": round(sim_struct, 4),
                "sim_text": round(sim_text, 4),
                "genre_boost": round(genre_boost, 4) if user_genre_profile else 0.0,
                "genre_similarity": round(g_sim, 4),
                "api_similar": c_id in api_similar,
                "api_recommended": c_id in api_recommended,
                "rating_norm": round(nr, 3),
                "recency": round(rec, 3),
            })

    if scores:
        max_score = max(scores.values())  # нормализация итоговых баллов, наибольшее значение = 1.0, остальные - процент от наибольшего значения
        if max_score > 0:
            for c_id in list(scores.keys()):
                scores[c_id] = scores[c_id] / max_score

    result = sorted(scores.items(), key=lambda x: x[1], reverse=True)  # итог: список кортежей, cортируем пары (movie_id, score) по убыванию score

    return [   # возвращаем список словарей
        {
            "movie_id": c_id,  # id фильма-рекомендации
            "score": score,  # нормализованный score (вес) фильма-рекомендации
            "reasons": reasons[c_id]   # объяснения, почему этот фильм
        }
        for c_id, score in result
    ]
