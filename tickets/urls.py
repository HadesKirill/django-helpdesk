from django.urls import path

from .views import (
    TicketCreateView,
    TicketDetailView,
    TicketListView,
    TicketStatusUpdateView,
    TicketCommentCreateView,
)

app_name = "tickets"

urlpatterns = [
    path("", TicketListView.as_view(), name="list"),
    path(
        "tickets/create/",
        TicketCreateView.as_view(),
        name="create",
    ),
    path(
        "tickets/<int:pk>/",
        TicketDetailView.as_view(),
        name="detail",
    ),
    path(
        "tickets/<int:pk>/status/",
        TicketStatusUpdateView.as_view(),
        name="status",
    ),
    path(
        "tickets/<int:pk>/comments/add/",
        TicketCommentCreateView.as_view(),
        name="comment_create",
    ),
]