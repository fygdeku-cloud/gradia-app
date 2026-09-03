/* ============================================================
   Gradia — Messages Django (toasts/alertes Flowbite)
   Fermeture manuelle + disparition automatique selon le niveau.
   Aucune donnée sensible manipulée.
   ============================================================ */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var stack = document.querySelector("#gradia-message-stack");
    if (!stack) {
      return;
    }

    var items = stack.querySelectorAll("[data-gradia-message]");
    items.forEach(function (el) {
      var delay = parseInt(el.dataset.gradiaMessage, 10) || 6000;

      setTimeout(function () {
        el.classList.add("opacity-0", "transition-opacity", "duration-300");
        setTimeout(function () {
          el.remove();
        }, 320);
      }, delay);

      var close = el.querySelector("[data-gradia-message-close]");
      if (close) {
        close.addEventListener("click", function () {
          el.remove();
        });
      }
    });
  });
})();