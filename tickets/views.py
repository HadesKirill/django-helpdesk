from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from accounts.models import User

from .forms import TicketCreateForm
from .models import Ticket


class TicketAccessMixin:
    """Общий отбор доступных заявок для списка и подробностей."""

    def get_queryset(self):
        user = self.request.user

        queryset = Ticket.objects.select_related(
            "customer",
            "assignee",
            "category",
            "equipment",
        )

        if user.is_superuser:
            return queryset

        if user.role == User.Role.CUSTOMER:
            return queryset.filter(customer=user)

        if user.role == User.Role.TECHNICIAN:
            return queryset.filter(assignee=user)

        return queryset.none()


class TicketListView(
    LoginRequiredMixin,
    TicketAccessMixin,
    ListView,
):
    model = Ticket
    template_name = "tickets/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 10


class TicketDetailView(
    LoginRequiredMixin,
    TicketAccessMixin,
    DetailView,
):
    model = Ticket
    template_name = "tickets/ticket_detail.html"
    context_object_name = "ticket"


class TicketCreateView(
    LoginRequiredMixin,
    UserPassesTestMixin,
    CreateView,
):
    model = Ticket
    form_class = TicketCreateForm
    template_name = "tickets/ticket_form.html"

    def test_func(self):
        return self.request.user.role == User.Role.CUSTOMER

    def form_valid(self, form):
        form.instance.customer = self.request.user
        form.instance.status = Ticket.Status.NEW
        form.instance.assignee = None
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "tickets:detail",
            kwargs={"pk": self.object.pk},
        )