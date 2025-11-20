from collections import defaultdict
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

    def __init__(self):
        self.index = defaultdict(set)

    def add_movie(self, movie_id: str, features: dict) -> None:
        """
        Фильмы:
        movie 1: features = {"genre:Sci-Fi", "actor:Tom Hardy", "director:Nolan"}
        movie 2: features = {"genre:Drama", "actor:DiCaprio", "director:Nolan"}
        movie 3: features = {"genre:Sci-Fi", "actor:DiCaprio", "director:Somebody"}
        movie 4: features = {"genre:Comedy", "actor:Someone", "director:SomeoneElse"}
        Просмотрен movie 1 ->
        self.index = {"genre:Sci-Fi": {1, 3}, "actor:Tom Hardy": {1},
                      "director:Nolan": {1, 2}, "genre:Drama": {2},
                      "actor:DiCaprio": {2,3}, "genre:Comedy": {4},...}
        """
        for f in features:
            self.index[f].add(movie_id)

    def candidates_for(self, features: dict):
        """
        Возвращает set кандидатов, которые совпадают хотя бы по одному признаку.
        Оператор |= (in-place union) добавляет все id из self.index[f] в cand:
        {1,2,3}
        """
        cand = set()
        for f in features:
            cand |= self.index.get(f, set())
        return cand


class TextSimilarity:

    def __init__(self, movies):
        """movies — список фильмов ORM"""
        texts = [
            (m.id, (m.overview or "") + " " + (m.tagline or ""))
            for m in movies
        ]
        self.ids = [m[0] for m in texts]
        corpus = [m[1] for m in texts]

        self.vectorizer = TfidfVectorizer(max_features=5000)
        self.matrix = self.vectorizer.fit_transform(corpus)

    def similarity(self, id_a, id_b):
        try:
            idx_a = self.ids.index(id_a)
            idx_b = self.ids.index(id_b)
        except ValueError:
            return 0

        v1 = self.matrix[idx_a]
        v2 = self.matrix[idx_b]
        return cosine_similarity(v1, v2)[0][0]
