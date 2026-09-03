/* ============================================================
   Gradia — Saisie OTP à 6 cases (amélioration progressive)

   Le champ Django réel (name="code") reste la SOURCE DE VÉRITÉ :
   - les cases ne font que déplacer le focus, gérer Backspace,
     le collage et synchroniser leur contenu vers le champ réel ;
   - la validation, le stockage et l'envoi restent 100 % Django.

   Ce script ne valide AUCUNE sécurité, ne stocke jamais l'OTP
   (ni localStorage, ni sessionStorage, ni console) et n'envoie
   aucune donnée vers un service extérieur.
   ============================================================ */
(function () {
  "use strict";

  function initOtpBoxes(root) {
    var realInput = root.querySelector('input[name="code"]');
    var list = root.querySelector("[data-otp-boxes-list]");
    var fallback = root.querySelector("[data-otp-fallback]");

    if (!realInput || !list || !fallback) {
      return;
    }

    var length = parseInt(realInput.maxLength, 10) || 6;
    var boxes = Array.prototype.slice.call(list.querySelectorAll(".otp-box"));

    if (boxes.length !== length) {
      return;
    }

    function syncToReal() {
      realInput.value = boxes
        .map(function (box) {
          return box.value;
        })
        .join("");
    }

    function syncFromReal() {
      var value = realInput.value || "";
      boxes.forEach(function (box, index) {
        box.value = value.charAt(index) || "";
      });
    }

    function focusBox(index) {
      if (boxes[index]) {
        boxes[index].focus();
      }
    }

    boxes.forEach(function (box, index) {
      box.addEventListener("input", function () {
        var digits = box.value.replace(/\D/g, "");
        box.value = digits.slice(-1);

        if (box.value && index < length - 1) {
          focusBox(index + 1);
        }
        syncToReal();
      });

      box.addEventListener("keydown", function (event) {
        if (event.key === "Backspace" && !box.value && index > 0) {
          event.preventDefault();
          var previous = boxes[index - 1];
          previous.value = "";
          focusBox(index - 1);
          syncToReal();
        }
      });

      box.addEventListener("paste", function (event) {
        event.preventDefault();
        var text = (event.clipboardData || window.clipboardData)
          .getData("text")
          .replace(/\D/g, "")
          .slice(0, length);

        text.split("").forEach(function (char, offset) {
          var target = boxes[index + offset];
          if (target) {
            target.value = char;
          }
        });

        var target = Math.min(index + text.length, length - 1);
        syncToReal();
        focusBox(target);
      });
    });

    realInput.addEventListener("input", syncFromReal);

    var form = realInput.form;
    if (form) {
      form.addEventListener("submit", syncToReal);
    }

    // Active l'interface 6 cases uniquement si le script s'exécute.
    fallback.classList.add("hidden");
    list.classList.remove("hidden");
    syncFromReal();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-otp-boxes]").forEach(initOtpBoxes);
  });
})();