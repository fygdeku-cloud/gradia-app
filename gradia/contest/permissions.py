from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _


class StudentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Restreint l'accès aux vues `contest` aux étudiants inscrits.

    Règle métier :
    - visiteur anonyme            -> redirection vers `users:login` avec `?next=` ;
    - utilisateur connecté mais
      non étudiant (`is_student`
      à `False`)                 -> redirection vers `users:profile`
                                    (inscription au profil étudiant),
                                    avec `?next=`.

    L'URL demandée est conservée dans `?next=` afin que l'utilisateur
    retrouve la page du concours une fois son profil étudiant complété.
    """

    login_url = reverse_lazy("users:login")
    student_profile_url = reverse_lazy("users:profile")

    def test_func(self):
        return bool(getattr(self.request.user, "is_student", False))

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            # Visiteur anonyme : LoginRequiredMixin redirige vers `users:login`.
            return super().handle_no_permission()

        # Utilisateur authentifié mais non étudiant.
        return self.redirect_to_student_profile()

    def redirect_to_student_profile(self):
        """Redirige vers l'inscription/mise à jour du profil étudiant."""
        messages.info(
            self.request,
            _(
                "Les concours sont réservés aux étudiants. "
                "Complétez votre profil étudiant pour y accéder.",
            ),
        )
        next_url = quote(self.request.get_full_path(), safe="")
        return redirect(f"{self.student_profile_url}?next={next_url}")
