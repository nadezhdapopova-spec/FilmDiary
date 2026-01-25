from django.urls import path
from calendar_events.views_pages import CalendarListPageView

app_name = "calendar_events_pages"

urlpatterns = [
    path("calendar_list/", CalendarListPageView.as_view(), name="calendar_list"),
]