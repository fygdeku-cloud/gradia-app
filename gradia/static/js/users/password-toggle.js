(function () {
  "use strict";

  function initPasswordToggle(input) {
    if (!input.id || input.dataset.passwordToggleReady) {
      return;
    }

    var wrapper = input.parentElement;
    if (!wrapper) {
      return;
    }

    var button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle";
    button.setAttribute("aria-label", "Afficher le mot de passe");
    button.title = "Afficher le mot de passe";
    button.innerHTML = "<span aria-hidden=\"true\">&#9673;</span>";

    wrapper.classList.add("password-field");
    wrapper.appendChild(button);
    input.dataset.passwordToggleReady = "true";

    button.addEventListener("click", function () {
      var visible = input.type === "text";
      input.type = visible ? "password" : "text";
      button.setAttribute(
        "aria-label",
        visible ? "Afficher le mot de passe" : "Masquer le mot de passe"
      );
      button.title = visible ? "Afficher le mot de passe" : "Masquer le mot de passe";
      button.innerHTML = visible
        ? "<span aria-hidden=\"true\">&#9673;</span>"
        : "<span aria-hidden=\"true\">&#9675;</span>";
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    document
      .querySelectorAll('.gradia-field input[type="password"]')
      .forEach(initPasswordToggle);
  });
})();
