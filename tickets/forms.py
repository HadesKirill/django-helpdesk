from django import forms

from .models import Category, Comment, Ticket

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

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Уточните проблему или сообщите о результате",
                }
            ),
        }

    def clean_text(self):
        text = self.cleaned_data["text"].strip()

        if not text:
            raise forms.ValidationError(
                "Комментарий не может быть пустым."
            )

        return text

class TicketFilterForm(forms.Form):
    q = forms.CharField(
        label="Поиск",
        required=False,
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Название, описание или инвентарный номер",
            }
        ),
    )
    status = forms.ChoiceField(
        label="Статус",
        required=False,
        choices=[("", "Все статусы")] + list(Ticket.Status.choices),
    )
    priority = forms.ChoiceField(
        label="Приоритет",
        required=False,
        choices=[("", "Все приоритеты")] + list(Ticket.Priority.choices),
    )
    category = forms.ModelChoiceField(
        label="Категория",
        required=False,
        queryset=Category.objects.all(),
        empty_label="Все категории",
    )
    overdue = forms.BooleanField(
        label="Только просроченные",
        required=False,
    )