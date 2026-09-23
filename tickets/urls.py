from django.urls import path

from .views import (
    TicketCreateView,
    TicketDetailView,
    TicketListView,
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
]