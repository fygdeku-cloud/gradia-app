/* ============================================================
   Gradia — Dashboard : menus déroulants utilisateur
   Les dropdowns Flowbite (data-dropdown-toggle) sont déjà gérés
   par flowbite.min.js (CDN). Ce fichier est volontairement léger :
   il garantit que le menu est fermable avec la touche Échap
   et améliore l'accessibilité clavier.
   ============================================================ */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var toggles = document.querySelectorAll("[data-dropdown-toggle]");

    toggles.forEach(function (toggle) {
      toggle.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          document.body.click();
        }
      });
    });
  });
})();