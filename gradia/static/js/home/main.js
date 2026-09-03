/* ============================================================
   Gradia — Micro-interactions de la navbar (home)
   Ombre portée au scroll, uniquement. Léger et sans dépendance.
   ============================================================ */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var header = document.querySelector("[data-gradia-navbar]");
    if (!header) {
      return;
    }

    var onScroll = function () {
      if (window.scrollY > 4) {
        header.classList.add("shadow-sm");
      } else {
        header.classList.remove("shadow-sm");
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  });
})();