(function () {
  function isChecked(image) {
    return image && image.getAttribute("aria-checked") !== "false";
  }

  function setAgreementState(image, checked) {
    if (!image) {
      return;
    }
    image.src = checked ? "assets/check.svg" : "assets/uncheck.svg";
    image.alt = checked ? "{{wechat.agreementChecked}}" : "{{wechat.agreementUnchecked}}";
    image.setAttribute("aria-checked", checked ? "true" : "false");
  }

  window.togglePortalAgreement = function (image) {
    var checked = !isChecked(image);
    if (typeof toggleAgreeCheck === "function" && window.jQuery) {
      try {
        toggleAgreeCheck($(image));
      } catch (_error) {}
    }
    setAgreementState(image, checked);
  };

  function init() {
    var agreement = document.getElementById("agreeCheck");
    if (!agreement) {
      return;
    }
    agreement.setAttribute("tabindex", "0");
    agreement.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        window.togglePortalAgreement(agreement);
      }
    }, false);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, false);
  } else {
    init();
  }
})();
