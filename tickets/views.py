from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from accounts.models import User

from .forms import CommentForm, TicketCreateForm, TicketFilterForm
from .models import Ticket

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from .services import change_ticket_status, get_status_actions

from django.db.models import Count, Q
from django.utils import timezone

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

    def get_queryset(self):
        # Сначала ограничиваем доступ, затем применяем поиск.
        self.visible_tickets = super().get_queryset()

        self.active_filter = Q(
            status__in=[
                Ticket.Status.NEW,
                Ticket.Status.IN_PROGRESS,
            ]
        )
        self.overdue_filter = (
            self.active_filter & Q(due_at__lt=timezone.now())
        )

        self.filter_form = TicketFilterForm(self.request.GET)
        queryset = self.visible_tickets

        if not self.filter_form.is_valid():
            return queryset.none()

        filters = self.filter_form.cleaned_data
        search = filters["q"]

        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(equipment__inventory_number__icontains=search)
            )

        if filters["status"]:
            queryset = queryset.filter(status=filters["status"])

        if filters["priority"]:
            queryset = queryset.filter(priority=filters["priority"])

        if filters["category"]:
            queryset = queryset.filter(category=filters["category"])

        if filters["overdue"]:
            queryset = queryset.filter(self.overdue_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form

        context["stats"] = self.visible_tickets.aggregate(
            total=Count("pk"),
            active=Count("pk", filter=self.active_filter),
            resolved=Count(
                "pk",
                filter=Q(status=Ticket.Status.RESOLVED),
            ),
            overdue=Count("pk", filter=self.overdue_filter),
        )

        return context


class TicketDetailView(
    LoginRequiredMixin,
    TicketAccessMixin,
    DetailView,
):
    model = Ticket
    template_name = "tickets/ticket_detail.html"
    context_object_name = "ticket"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["status_actions"] = get_status_actions(
            self.object,
            self.request.user,
        )
        context["status_history"] = (
            self.object.status_history.select_related("actor")
        )
        context["comments"] = (
            self.object.comments.select_related("author")
        )
        context["comment_form"] = CommentForm()
        return context


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

class TicketStatusUpdateView(
    LoginRequiredMixin,
    TicketAccessMixin,
    View,
):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        ticket = get_object_or_404(
            self.get_queryset(),
            pk=kwargs["pk"],
        )

        try:
            change_ticket_status(
                ticket_id=ticket.pk,
                actor=request.user,
                new_status=request.POST.get("status", ""),
            )
        except ValidationError as error:
            messages.error(request, error.messages[0])
        else:
            messages.success(request, "Статус заявки обновлён.")

        return redirect("tickets:detail", pk=ticket.pk)


class TicketCommentCreateView(TicketDetailView):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CommentForm(request.POST)

        if form.is_valid():
            comment = form.save(commit=False)
            comment.ticket = self.object
            comment.author = request.user
            comment.save()

            messages.success(request, "Комментарий добавлен.")

            return redirect(
                "tickets:detail",
                pk=self.object.pk,
            )

        context = self.get_context_data()
        context["comment_form"] = form

        return self.render_to_response(context, status=400)