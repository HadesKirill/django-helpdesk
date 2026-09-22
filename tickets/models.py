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