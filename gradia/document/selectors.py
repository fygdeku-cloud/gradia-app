"""
Lectures (uniquement) du module Document.
requetes necessaires pour retrouver des documents, achat, paiement et acces
"""

from django.db.models import BooleanField, Exists, OuterRef, Q, Value

from gradia.document.models import Document, DocumentAccessLog
from gradia.payment.models import Payment
from gradia.utils.enums import OrderStatus, PaymentStatus, PaymentType


def get_documents():
    """Tous les documents avec leurs relations principales préchargées."""
    return Document.objects.select_related(
        "contest_session__contest__establishment",
        "contest_session__contest__category",
    ).order_by("title")


def get_published_documents():
    """Documents publiés, visibles dans le catalogue public."""
    return get_documents().filter(is_published=True)


def get_manageable_documents():
    """Tous les documents (publiés ou non) pour la gestion."""
    return get_documents().order_by("-updated_at")


def get_document_detail(document_id):
    return get_documents().filter(pk=document_id).first()


def get_published_document_detail(document_id):
    return get_published_documents().filter(pk=document_id).first()


def get_documents_for_session(session):
    return get_documents().filter(contest_session=session)


def get_published_documents_for_session(session):
    return get_published_documents().filter(contest_session=session)


def get_documents_for_contest(contest):
    return get_documents().filter(contest_session__contest=contest)


def get_published_documents_for_contest(contest):
    return get_published_documents().filter(contest_session__contest=contest)


def get_documents_for_category(category):
    return get_documents().filter(contest_session__contest__category=category)


def get_published_documents_for_category(category):
    return get_published_documents().filter(contest_session__contest__category=category)


def get_documents_for_establishment(establishment):
    return get_documents().filter(contest_session__contest__establishment=establishment)


def get_published_documents_for_establishment(establishment):
    return get_published_documents().filter(contest_session__contest__establishment=establishment)


def search_documents(queryset=None, query=""):
    queryset = queryset or get_documents()
    query = query.strip()
    if not query:
        return queryset
    return queryset.filter(
        Q(title__icontains=query)
        | Q(description__icontains=query)
        | Q(context__icontains=query)
        | Q(contest_session__contest__title__icontains=query)
        | Q(contest_session__contest__establishment__title__icontains=query)
    )


# ---------------------------------------------------------------------------
# Paiement / accès
# ---------------------------------------------------------------------------

def _confirmed_charge_payments_for_user(user):
    """
    Paiements de type « charge » confirmés d'un utilisateur.

    - status = SUCCESS (paiement réellement réglé) ;
    - order.status = SUCCESS (commande confirmée) ;
    - transaction_type = CHARGE (les remboursements ne sont jamais
      considérés comme des paiements).
    """
    return Payment.objects.filter(
        order__student=user,
        order__status=OrderStatus.SUCCESS,
        transaction_type=PaymentType.CHARGE,
        status=PaymentStatus.SUCCESS,
    )


def _exclude_refunded(queryset):
    """
    Exclut des paiements les commandes qui ont ensuite fait l'objet
    d'un remboursement (total ou partiel).
    """
    refunded = Payment.objects.filter(
        order=OuterRef("order"),
        transaction_type__in=[PaymentType.REFUND, PaymentType.PARTIAL_REFUND],
        status__in=[PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED],
    )
    return queryset.annotate(has_refund=Exists(refunded)).filter(has_refund=False)


def has_confirmed_payment(user, document):
    """
    Indique si l'utilisateur dispose d'un droit d'accès au document
    (paiement confirmé) — ou si le document est gratuit.

    Critères (tous requis pour un document payant) :
    - une commande SUCCESS contenant le document ;
    - un paiement de type CHARGE au statut SUCCESS ;
    - aucun remboursement sur la commande.
    """
    if not user or not user.is_authenticated:
        return False
    if document.price <= 0:
        return True

    payments = _exclude_refunded(
        _confirmed_charge_payments_for_user(user).filter(
            order__items__document=document,
        )
    )
    return payments.exists()
def get_paid_document_ids_for_user(user):
    """Identifiants des documents payés (paiement confirmé) par un étudiant."""
    if not user or not user.is_authenticated:
        return Document.objects.none().values_list("pk", flat=True)

    payments = _exclude_refunded(
        _confirmed_charge_payments_for_user(user).filter(
            order__items__document=OuterRef("pk"),
        )
    )
    return (
        Document.objects.filter(price__gt=0)
        .filter(Exists(payments))
        .values_list("pk", flat=True)
    )


def get_user_purchased_documents(user):
    """Documents réellement achetés par un utilisateur (paiement confirmé)."""
    if not user or not user.is_authenticated:
        return Document.objects.none()
    return get_documents().filter(pk__in=get_paid_document_ids_for_user(user))


def annotate_with_paid_status(queryset, user):
    """
    Annote un QuerySet de documents avec ``has_paid``.

    Permet d'afficher l'état « payé » d'une liste de documents sans multiplier
    les requêtes de paiement (évite le problème N+1).
    """
    if not user or not user.is_authenticated:
        return queryset.annotate(
            has_paid=Value(False, output_field=BooleanField())
        )

    payments = _exclude_refunded(
        _confirmed_charge_payments_for_user(user).filter(
            order__items__document=OuterRef("pk"),
        )
    )
    return queryset.annotate(has_paid=Exists(payments))


def get_accessible_documents(user):
    """
    Documents accessibles à un utilisateur.

    - Documents gratuits publiés : accessibles à tout le monde ;
    - Documents payants publiés : accessibles après paiement confirmé ;
    - Staff / administrateurs : tous les documents.
    """
    queryset = get_documents()
    if not user or not user.is_authenticated:
        return queryset.filter(is_published=True, price=0)
    if user.is_staff or user.is_superuser:
        return queryset

    payments = _exclude_refunded(
        _confirmed_charge_payments_for_user(user).filter(
            order__items__document=OuterRef("pk"),
        )
    )
    return queryset.filter(
        is_published=True,
    ).filter(
        Q(price=0) | Exists(payments),
    )


# ---------------------------------------------------------------------------
# Journal d'accès (lecture)
# ---------------------------------------------------------------------------

def get_document_access_logs(user, limit=None):
    """Historique des accès aux documents d'un utilisateur."""
    queryset = DocumentAccessLog.objects.filter(user=user).select_related(
        "document",
        "document__contest_session",
    ).order_by("-accessed_at")
    if limit:
        queryset = queryset[:limit]
    return queryset


def get_all_document_access_logs(limit=None):
    """Journal complet des accès, destiné aux administrateurs."""
    queryset = DocumentAccessLog.objects.select_related(
        "user",
        "document",
        "document__contest_session",
    ).order_by("-accessed_at")
    if limit:
        queryset = queryset[:limit]
    return queryset
