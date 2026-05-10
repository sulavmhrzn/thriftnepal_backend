from rest_framework.pagination import CursorPagination


class DefaultCursorPagination(CursorPagination):
    page_size = 20
    ordering = "-created_at"
    cursor_query_param = "cursor"
    page_size_query_param = "page_size"
    max_page_size = 100


class SmallCursorPagination(DefaultCursorPagination):
    page_size = 10


class LargeCursorPagination(DefaultCursorPagination):
    page_size = 50
