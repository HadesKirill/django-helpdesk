from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User

from .models import Ticket, TicketStatusHistory


def get_status_actions(ticket, user):
    """Возвращает доступные пользователю действия над заявкой."""
    if not user.is_authenticated or not user.is_active:
        return {}

    is_assignee = (
        user.role == User.Role.TECHNICIAN
        and ticket.assignee_id == user.pk
    )
    is_customer = (
        user.role == User.Role.CUSTOMER
        and ticket.customer_id == user.pk
    )

    if user.is_superuser or is_assignee:
        if ticket.status == Ticket.Status.NEW and ticket.assignee_id:
            return {
                Ticket.Status.IN_PROGRESS: "Взять в работу",
            }

        if ticket.status == Ticket.Status.IN_PROGRESS:
            return {
                Ticket.Status.RESOLVED: "Отметить выполнение",
            }

    if user.is_superuser or is_customer:
        if ticket.status == Ticket.Status.RESOLVED:
            return {
                Ticket.Status.CLOSED: "Подтвердить и закрыть",
            }

    return {}


def change_ticket_status(*, ticket_id, actor, new_status):
    """Проверяет переход, меняет статус и записывает историю."""
    ticket = Ticket.objects.get(pk=ticket_id)

    allowed_actions = get_status_actions(ticket, actor)
    if new_status not in allowed_actions:
        raise PermissionDenied(
            "Этот переход статуса вам недоступен."
        )

    old_status = ticket.status

    with transaction.atomic():
        updated = Ticket.objects.filter(
            pk=ticket.pk,
            status=old_status,
            customer_id=ticket.customer_id,
            assignee_id=ticket.assignee_id,
        ).update(
            status=new_status,
            updated_at=timezone.now(),
        )

        if updated != 1:
            raise ValidationError(
                "Заявка уже изменилась. Обновите страницу."
            )

        TicketStatusHistory.objects.create(
            ticket_id=ticket.pk,
            actor=actor,
            old_status=old_status,
            new_status=new_status,
        )