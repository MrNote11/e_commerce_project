from rest_framework import pagination
from rest_framework.response import Response

class CustomPagination(pagination.PageNumberPagination):
    page_size = 50
    max_page_size = 100
    page_size_query_param = "page_size"
    page_query_param = "page"

    def get_paginated_response(self, data):
        return Response({
            "count": self.page.paginator.count,  # Total count of items
            "next": self.get_next_link(),  # URL for the next page, if available
            "previous": self.get_previous_link(),  # URL for the previous page, if available
            "results": data,  # Paginated results
        })
