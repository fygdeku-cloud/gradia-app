from gradia.cart.models import Cart


def get_cart_for_student(student):
    """Return the student's cart with its document details loaded."""
    return (
        Cart.objects.filter(student=student)
        .prefetch_related(
            "items__document__contest_session__contest__category",
            "items__document__contest_session__contest__establishment",
        )
        .first()
    )
