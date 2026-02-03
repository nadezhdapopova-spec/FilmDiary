from rest_framework.pagination import PageNumberPagination


class CalendarEventPaginator(PageNumberPagination):
    """Настраивает пагинацию для списка запланированных к просмотру фильмов (по 12 на странице)"""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 12
