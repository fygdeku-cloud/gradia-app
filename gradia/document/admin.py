from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from gradia.document.models import Document, DocumentAccessLog


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "contest_session",
        "price",
        "is_published",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_published", "contest_session", "price")
    search_fields = ("title", "context", "description")
    list_select_related = ("contest_session__contest__establishment",)
    date_hierarchy = "created_at"
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            _("Contenu"),
            {
                "fields": (
                    "title",
                    "description",
                    "context",
                    "contest_session",
                )
            },
        ),
        (
            _("Fichiers"),
            {
                "fields": (
                    "subject_file",
                    "correction_file",
                ),
                "description": _(
                    "Les fichiers sont stockés dans un stockage protégé : "
                    "ils ne sont accessibles que via les vues contrôlées de "
                    "l'application (jamais directement par URL)."
                ),
            },
        ),
        (
            _("Vente et publication"),
            {
                "fields": (
                    "price",
                    "is_published",
                )
            },
        ),
        (
            _("Horodatage"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(DocumentAccessLog)
class DocumentAccessLogAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "document",
        "action",
        "accessed_at",
    )
    list_filter = ("action", "accessed_at")
    search_fields = (
        "user__email",
        "document__title",
    )
    list_select_related = ("user", "document")
    date_hierarchy = "accessed_at"
    readonly_fields = (
        "user",
        "document",
        "action",
        "accessed_at",
        "created_at",
    )

    def has_add_permission(self, request):
        # Les journaux sont créés uniquement par le service d'accès.
        return False

    def has_change_permission(self, request, obj=None):
        # Les journaux sont immuables après création (traçabilité).
        return False
