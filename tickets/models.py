from django.conf import settings
from django.db import models


class Equipment(models.Model):
    name = models.CharField("Название", max_length=150)
    inventory_number = models.CharField(
        "Инвентарный номер",
        max_length=50,
        unique=True,
    )
    location = models.CharField("Расположение", max_length=150)
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"
        ordering = ["name", "id"]

    def __str__(self):
        return f"{self.name} ({self.inventory_number})"


class Category(models.Model):
    name = models.CharField(
        "Название",
        max_length=100,
        unique=True,
    )
    description = models.TextField("Описание", blank=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Новая"
        IN_PROGRESS = "in_progress", "В работе"
        RESOLVED = "resolved", "Выполнена"
        CLOSED = "closed", "Закрыта"

    class Priority(models.TextChoices):
        LOW = "low", "Низкий"
        NORMAL = "normal", "Обычный"
        HIGH = "high", "Высокий"

    title = models.CharField("Название", max_length=200)
    description = models.TextField("Описание проблемы")

    equipment = models.ForeignKey(
        Equipment,
        verbose_name="Оборудование",
        on_delete=models.PROTECT,
        related_name="tickets",
        blank=True,
        null=True,
    )
    category = models.ForeignKey(
        Category,
        verbose_name="Категория",
        on_delete=models.PROTECT,
        related_name="tickets",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Заказчик",
        on_delete=models.PROTECT,
        related_name="created_tickets",
        limit_choices_to={"role": "customer"},
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Исполнитель",
        on_delete=models.PROTECT,
        related_name="assigned_tickets",
        limit_choices_to={"role": "technician"},
        blank=True,
        null=True,
    )

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    priority = models.CharField(
        "Приоритет",
        max_length=20,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )

    created_at = models.DateTimeField(
        "Создана",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        "Обновлена",
        auto_now=True,
    )
    due_at = models.DateTimeField(
        "Срок выполнения",
        blank=True,
        null=True,
    )

    class Meta:
        verbose_name = "Заявка"
        verbose_name_plural = "Заявки"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title

class TicketStatusHistory(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Кто изменил",
        on_delete=models.PROTECT,
        related_name="ticket_status_changes",
    )
    old_status = models.CharField(
        "Предыдущий статус",
        max_length=20,
        choices=Ticket.Status.choices,
    )
    new_status = models.CharField(
        "Новый статус",
        max_length=20,
        choices=Ticket.Status.choices,
    )
    created_at = models.DateTimeField(
        "Дата изменения",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Изменение статуса"
        verbose_name_plural = "История статусов"
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return (
            f"Заявка №{self.ticket_id}: "
            f"{self.get_old_status_display()} → "
            f"{self.get_new_status_display()}"
        )

class Comment(models.Model):
    ticket = models.ForeignKey(
        Ticket,
        verbose_name="Заявка",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        on_delete=models.PROTECT,
        related_name="ticket_comments",
    )
    text = models.TextField(
        "Комментарий",
        max_length=2000,
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"Комментарий #{self.pk} к заявке #{self.ticket_id}"