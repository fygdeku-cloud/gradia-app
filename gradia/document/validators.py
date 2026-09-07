from pathlib import Path

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from gradia.utils.enums import _MAGIC_SIGNATURES, ALLOWED_EXTENSIONS
from gradia.utils.enums import  ALLOWED_CONTENT_TYPES, MAX_DOCUMENT_SIZE

def validate_document_file(uploaded_file):
    """Valide un fichier soumis pour un document (sujet ou corrigé)."""
    if not uploaded_file:
        return

    # 1. Extension autorisée (première barrière, jamais suffisante).
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValidationError(_("Only PDF, DOC or DOCX files are allowed."))

    # 2. Taille maximale.
    if uploaded_file.size > MAX_DOCUMENT_SIZE:
        raise ValidationError(_("The document must not exceed 25 MB."))

    # 3. Type MIME déclaré par le client (indicateur, ne fait pas foi).
    content_type = getattr(uploaded_file, "content_type", None)
    if content_type and content_type not in ALLOWED_CONTENT_TYPES:
        raise ValidationError(_("The uploaded file type is not allowed."))

    # 4. Nom de fichier sûr : aucun séparateur de chemin autorisé.
    if Path(uploaded_file.name).name != uploaded_file.name:
        raise ValidationError(_("The file name is invalid."))

    # 5. Contenu réel : signature (octets magiques) du fichier.
    _validate_file_signature(uploaded_file, suffix)


def _validate_file_signature(uploaded_file, suffix):
    """
    Vérifie les premiers octets du fichier pour confirmer son vrai format.
    S'appuie sur les signatures binaires connues sans dépendance externe :
    PDF      : commence par ``%PDF-`` DOC/DOCX : archive ZIP (``PK\\x03\\x04``).
    Le fichier doit être positionné au début et est remis à sa position
    d'origine après contrôle.
    """
    initial_position = uploaded_file.tell() or 0
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(4)
        uploaded_file.seek(initial_position)
    except (OSError, AttributeError) as exc:
        raise ValidationError(
            _("Impossible de verifier le contenu du fichier")
            )from exc

    if not header:
        raise ValidationError(_("The uploaded file is empty."))

    matched_format = None
    for signature, fmt in _MAGIC_SIGNATURES.items():
        if header.startswith(signature):
            matched_format = fmt
            break

    if matched_format is None:
        raise ValidationError(
            _("The uploaded file content does not match an allowed format (PDF, DOC or DOCX).")
        )

    # Cohérence extension / contenu réel.
    if suffix == ".pdf" and matched_format != "PDF":
        raise ValidationError(
            _("The uploaded file is not a valid PDF file.")
        )
    if suffix in {".doc", ".docx"} and matched_format != "DOCX/DOC (Zip archive)":
        raise ValidationError(
            _("The uploaded file is not a valid DOC/DOCX file.")
        )


def validate_document_files(subject_file, correction_file):
    validate_document_file(subject_file)
    validate_document_file(correction_file)


def validate_subject_file(subject_file):
    validate_document_file(subject_file)


def validate_correction_file(correction_file):
    validate_document_file(correction_file)
