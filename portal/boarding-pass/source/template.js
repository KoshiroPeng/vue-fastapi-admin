(function () {
  function isChecked(image) {
    return image && image.getAttribute("aria-checked") !== "false";
  }

  function setAgreementState(image, checked) {
    if (!image) {
      return;
    }
    image.src = checked ? "assets/check.svg" : "assets/uncheck.svg";
    image.alt = checked ? "{{boarding.agreementChecked}}" : "{{boarding.agreementUnchecked}}";
    image.setAttribute("aria-checked", checked ? "true" : "false");
  }

  function syncLoginButton() {
    var button = document.getElementById("loginBtn");
    var agreement = document.getElementById("agreeCheck");
    var fields = document.querySelectorAll(".auth-fields input");
    var complete = isChecked(agreement);
    var index;

    for (index = 0; index < fields.length; index += 1) {
      if (!fields[index].value.replace(/^\s+|\s+$/g, "")) {
        complete = false;
      }
    }
    if (button) {
      button.className = complete ? "login-button" : "login-button is-disabled";
    }
  }

  window.togglePortalAgreement = function (image) {
    var checked = !isChecked(image);
    if (typeof toggleAgreeCheck === "function" && window.jQuery) {
      try {
        toggleAgreeCheck($(image));
      } catch (_error) {}
    }
    setAgreementState(image, checked);
    syncLoginButton();
  };

  function init() {
    var fields = document.querySelectorAll(".auth-fields input");
    var agreement = document.getElementById("agreeCheck");
    var index;
    for (index = 0; index < fields.length; index += 1) {
      fields[index].addEventListener("input", syncLoginButton, false);
    }
    if (agreement) {
      agreement.setAttribute("tabindex", "0");
      agreement.addEventListener("keydown", function (event) {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          window.togglePortalAgreement(agreement);
        }
      }, false);
    }
    syncLoginButton();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, false);
  } else {
    init();
  }
})();
