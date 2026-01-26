from dataclasses import dataclass
from typing import List, Optional


@dataclass
class TmdbFilm:
    """Датакласс для создания фильма-кандидата при формировании рекомендаций пользователю"""
    tmdb_id: int
    title: str
    overview: str
    tagline: str
    genres: List[str]
    actors: List[str]
    director: Optional[str]
