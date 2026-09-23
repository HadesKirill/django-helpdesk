from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.urls import reverse
from django.views.generic import CreateView, DetailView, ListView

from accounts.models import User

from .forms import CommentForm, TicketCreateForm
from .models import Ticket

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from .services import change_ticket_status, get_status_actions

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