from django.contrib import admin
from .models import Ticket, TicketMessage

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ["id", "student", "status", "priority", "created_at"]
    list_filter = ["status", "priority"]
    search_fields = ["student__email", "student__username"]
    readonly_fields = ["id", "created_at", "updated_at"]

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ["id", "ticket", "sender", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["ticket__id", "sender__email"]
    readonly_fields = ["id", "created_at", "updated_at"]
