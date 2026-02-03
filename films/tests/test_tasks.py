from unittest.mock import ANY, Mock, patch

import pytest
from celery.exceptions import Retry

from films.tasks import recompute_all_recommendations, recompute_user_recommendations
from users.models import CustomUser


@pytest.mark.django_db
def test_successful_recomputation(db, user):
    """Тест успешного пересчета рекомендаций для пользователя"""
    with patch("films.tasks.build_recommendations") as mock_build:
        with patch("films.tasks.cache") as mock_cache:
            mock_build.return_value = []
            mock_cache.set.return_value = True

            result = recompute_user_recommendations.run(user.id)

            assert result is None
            assert mock_build.called
            assert mock_cache.set.called


@pytest.mark.django_db
def test_user_not_found(db, celery_eager, mock_logger, mock_cache):
    """Тест: пользователь не найден"""
    non_existent_id = 999
    result = recompute_user_recommendations.delay(non_existent_id).get()

    assert result is None
    mock_cache.set.assert_not_called()
    mock_logger.info.assert_called_with("Recs START: user=%s task=%s", non_existent_id, ANY)


@pytest.mark.django_db
def test_api_exception_retry(db, user, celery_eager, mock_logger, mock_cache, mock_tmdb):
    """Тест retry при ошибке API"""
    mock_tmdb.build_recommendations.side_effect = Exception("API error")

    with pytest.raises(Retry):
        recompute_user_recommendations.delay(user.id).get()

    mock_logger.exception.assert_called()


@pytest.mark.django_db
@patch("films.tasks.build_recommendations")
@patch("films.tasks.cache")
def test_task_simple(mock_cache, mock_build_recommendations, db, user):
    """Тест доступа к self.request.id"""
    mock_build_recommendations.return_value = []
    result = recompute_user_recommendations.run(user.id)

    assert result is None
    mock_build_recommendations.assert_called_once()
    mock_cache.set.assert_called_once()


@pytest.mark.django_db
@patch.object(recompute_user_recommendations, "delay")
def test_successful_all_recommendations(mock_delay, db, user, monkeypatch):
    """Тест успешного запуска рекомендаций для всех пользователей"""
    CustomUser.objects.create_user(username="user2", email="test2@test.ru", password="123")
    CustomUser.objects.create_user(username="user3", email="test3@test.ru", password="123")

    result = recompute_all_recommendations.run()

    assert result is None
    assert mock_delay.call_count >= 1
    mock_delay.assert_any_call(user.id)


def test_multiple_users_dispatch(db, celery_eager, mock_logger, monkeypatch):
    """Тест диспатча для нескольких пользователей"""
    CustomUser.objects.create_user(username="test4", email="test4@test.ru", password="123")

    mock_delay = Mock()
    monkeypatch.setattr(recompute_user_recommendations, "delay", mock_delay)

    recompute_all_recommendations.delay().get()

    assert mock_delay.call_count >= 1


def test_all_recommendations_exception(db, user, celery_eager, mock_logger, monkeypatch):
    """Тест обработки исключения в задаче для всех пользователей"""
    monkeypatch.setattr(CustomUser.objects, "values_list", Mock(side_effect=Exception("DB error")))

    with pytest.raises(Exception, match="DB error"):
        recompute_all_recommendations.delay().get()

    mock_logger.exception.assert_called_once()


@pytest.mark.django_db
def test_full_integration(db, user, film, user_film):
    """Интеграционный тест"""
    with patch("films.tasks.build_recommendations") as mock_build, patch("films.tasks.cache") as mock_cache:
        mock_build.return_value = [{"movie_id": film.tmdb_id, "score": 0.9}]
        mock_cache.set.return_value = True

        result = recompute_user_recommendations.run(user.id)

        assert result is None
        mock_build.assert_called_once_with(user, ANY)
        mock_cache.set.assert_called_once()
