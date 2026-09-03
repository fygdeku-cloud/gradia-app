/* ============================================================
   Gradia — Dashboard : gestion de la sidebar mobile
   Le panneau mobile utilise le composant Drawer de Flowbite
   (data-drawer-*). Ce script ne fait qu'un léger renfort :
   marquage du lien actif.
   ============================================================ */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var current = window.location.pathname;

    document.querySelectorAll("[data-dashboard-link]").forEach(function (link) {
      var href = link.getAttribute("href") || "";
      if (href !== "#" && current === href) {
        link.classList.add("active");
      }
    });
  });
})();