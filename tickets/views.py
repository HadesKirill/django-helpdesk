from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from accounts.models import User

from .models import Ticket


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "tickets/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 10

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