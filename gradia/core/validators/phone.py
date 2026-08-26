import phonenumbers
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


PHONE_ERROR_MESSAGE = _("Entrez un numero valide" "(exmp: +2376xxxxxxxx).")
#Transformer et valider le numero en E.164
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
    
    except phonenumbers.NumberParseException as exp:
        raise ValidationError(
            PHONE_ERROR_MESSAGE,
            code="Numero de telephone invalide",
        ) from exp

# Validation du numero
def validate_phone_number(value: str) -> None:

    if not value:
        return
    normalize_phone_number(value)