from django import forms

from .models import Comment, Ticket


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