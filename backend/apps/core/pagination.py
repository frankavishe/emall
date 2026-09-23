from rest_framework.pagination import PageNumberPagination


class LimitedPageNumberPagination(PageNumberPagination):
    """Opt-in ?page_size= on top of the project-wide default (settings.REST_FRAMEWORK["PAGE_SIZE"]
    = 20). Omitting page_size leaves existing callers' behavior unchanged; a caller may request
    fewer rows (e.g. a homepage widget) but never more than max_page_size."""

    page_size_query_param = "page_size"
    max_page_size = 24
