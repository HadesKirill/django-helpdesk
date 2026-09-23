from django import forms

from .models import Ticket


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "title",
            "description",
            "category",
            "equipment",
            "priority",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 6}),
        }