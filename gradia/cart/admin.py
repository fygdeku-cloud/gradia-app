from __future__ import annotations

from django.contrib import admin
from .models import Cart, CartItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("student", "status", "created_at")
    search_fields = ("student__email", "student__username")
    readonly_fields = ("student", "created_at", "updated_at")
    list_filter = ("status",)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("document", "cart", "unit_price", "added_at")
    search_fields = ("document__title", "cart__student__email")
    readonly_fields = ("cart", "document", "unit_price", "added_at")
    list_select_related = ("document", "cart")
