from django.contrib import admin

from gradia.contest.models import (
    Contest,
    ContestCategory,
    ContestSession,
    Establishment,
)


@admin.register(Establishment)
class EstablishmentAdmin(admin.ModelAdmin):
    list_display = ("title", "location", "slug", "created_at")
    search_fields = ("title", "name", "location", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("title",)


@admin.register(ContestCategory)
class ContestCategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created_at")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    ordering = ("title",)


class ContestSessionInline(admin.TabularInline):
    model = ContestSession
    extra = 0
    show_change_link = True


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "establishment", "slug", "created_at")
    list_filter = ("category", "establishment")
    search_fields = ("title", "slug", "category__title", "establishment__title")
    autocomplete_fields = ("category", "establishment")
    inlines = (ContestSessionInline,)
    ordering = ("title",)


@admin.register(ContestSession)
class ContestSessionAdmin(admin.ModelAdmin):
    list_display = (
        "contest",
        "title",
        "year",
        "registration_start_date",
        "registration_end_date",
        "exam_date",
    )
    list_filter = ("year", "contest__establishment", "contest__category")
    search_fields = ("title", "contest__title")
    autocomplete_fields = ("contest",)
    ordering = ("-year",)