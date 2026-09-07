from django import forms
from .models import Ticket, TicketMessage

class TicketCreateForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea, label="Message initial")

    class Meta:
        model = Ticket
        fields = ["title", "description", "priority"]

class TicketMessageForm(forms.ModelForm):
    class Meta:
        model = TicketMessage
        fields = ["message"]
