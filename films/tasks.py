from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from django.core.cache import cache

from services.recommendations import build_recommendations
from services.tmdb import Tmdb


logger = get_task_logger(__name__)
User = get_user_model()


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={"max_retries": 3})
def recompute_user_recommendations(self, user_id):
    try:
        logger.info("Recs START: user=%s task=%s", user_id, self.request.id)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return

        api = Tmdb()
        recs = build_recommendations(user, api)

        cache_key = f"recs:user:{user.id}"
        cache.set(cache_key, recs, 60 * 60 * 24)  # 24 часа
        logger.info("Recs SUCCESS: user=%s count=%s cache=%s",
                    user.id, len(recs), cache_key)
    except Exception as e:
        logger.exception("Recs FAIL: user=%s task=%s", user_id, self.request.id)
        raise


@shared_task(bind=True)
def recompute_all_recommendations(self):
    try:
        logger.info("Recs ALL START: task=%s", self.request.id)
        user_ids = list(User.objects.values_list("id", flat=True))
        for user_id in user_ids:
            recompute_user_recommendations.delay(user_id)

        logger.info("Recs ALL DISPATCHED: users=%s task=%s", len(user_ids), self.request.id)
    except Exception as e:
        logger.exception("Recs ALL FAIL: task=%s", self.request.id)
        raise
