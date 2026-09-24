from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class StudentRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and getattr(self.request.user, 'is_student', False)

    def handle_no_permission(self):
        # Un utilisateur identifié non-étudiant est refusé.
        # Un utilisateur anonyme est redirigé vers la connexion.
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()
