from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache

from services.recommendations import build_recommendations
from services.tmdb import Tmdb


User = get_user_model()

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def recompute_user_recommendations(self, user_id):
    try:
        user = User.objects.filter(id=user_id).first()
        if not user:
            return

        api = Tmdb()
        recs = build_recommendations(user, api)

        cache_key = f"recs:user:{user.id}"
        cache.set(cache_key, recs, 60 * 60 * 24)  # 24 часа
    except Exception as e:
        print(f"[recs error] user_id={user_id}, error={e}")
        raise


@shared_task
def recompute_all_recommendations():
    for user_id in User.objects.values_list("id", flat=True):
        recompute_user_recommendations.delay(user_id)
