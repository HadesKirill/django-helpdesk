from django.contrib import admin

from .models import Category, Equipment, Ticket


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "inventory_number", "location")
    search_fields = ("name", "inventory_number", "location")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "status",
        "priority",
        "customer",
        "assignee",
        "created_at",
    )
    list_display_links = ("id", "title")
    list_filter = ("status", "priority", "category")
    search_fields = (
        "title",
        "description",
        "equipment__inventory_number",
        "customer__username",
        "assignee__username",
    )
    readonly_fields = ("created_at", "updated_at")
    list_select_related = ("customer", "assignee")
    list_per_page = 25