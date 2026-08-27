import phonenumbers

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


PHONE_ERROR_MESSAGE = _(
    "Entrer un numero de telephone valide "
    "(exmp. +237699999999)."
)

# Convertir/Transformer en phone number
def normalize_phone_number(value: str) -> str:
    if not value:
        return value

    try:
        parsed = phonenumbers.parse(value)
        if not phonenumbers.is_valid_number(parsed):
            raise ValidationError(
                PHONE_ERROR_MESSAGE,
                code="Numero de telephone invalide",
            )
        return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)

    except phonenumbers.NumberParseException as excp:
        raise ValidationError(
            PHONE_ERROR_MESSAGE,
            code="Numero de telephone invalide",
        ) from excp

# Validation du numero de telephone
def validate_phone_number(value: str) -> None:
    #Valider un numero internationnale
    if not value:
        return
    normalize_phone_number(value)