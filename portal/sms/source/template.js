(function () {
  function getElements() {
    return {
      code: document.getElementById("js-groupId"),
      group: document.getElementById("groupId"),
      list: document.getElementById("groupid"),
      localNumber: document.getElementById("phone"),
      mobileNumber: document.getElementById("mobileNum")
    };
  }

  function showCountryList() {
    var elements = getElements();
    if (elements.list) {
      elements.list.style.display = "block";
    }
  }

  function hideCountryList() {
    var elements = getElements();
    if (elements.list) {
      elements.list.style.display = "none";
    }
  }

  function filterCountries() {
    var elements = getElements();
    var filter = elements.code.value.toUpperCase();
    var items = elements.list.getElementsByTagName("li");
    var index;

    for (index = 0; index < items.length; index += 1) {
      items[index].style.display = items[index].textContent.toUpperCase().indexOf(filter) >= 0 ? "block" : "none";
    }
  }

  function selectCountry(item) {
    var elements = getElements();
    var match = item.textContent.match(/\+\d+/);

    if (match) {
      elements.code.value = match[0];
    }
    elements.group.value = item.getAttribute("data-id") || "";
    hideCountryList();
  }

  function syncMobileNumber() {
    var elements = getElements();
    var countryCode = "+" + elements.code.value.replace(/[^0-9]/g, "");
    elements.mobileNumber.value = countryCode + elements.localNumber.value.replace(/^\+/, "");
  }

  function initCountrySelector() {
    var elements = getElements();
    var items;
    var index;

    if (!elements.code || !elements.list) {
      return;
    }

    items = elements.list.getElementsByTagName("li");
    elements.code.addEventListener("focus", showCountryList, false);
    elements.code.addEventListener("input", filterCountries, false);
    elements.code.addEventListener("blur", function () {
      window.setTimeout(hideCountryList, 150);
    }, false);

    for (index = 0; index < items.length; index += 1) {
      items[index].addEventListener("mousedown", function (event) {
        event.preventDefault();
        selectCountry(this);
      }, false);
      items[index].addEventListener("touchend", function (event) {
        event.preventDefault();
        selectCountry(this);
      }, false);
    }
  }

  window.SetInputNull = function () {
    var elements = getElements();
    elements.code.value = "";
    filterCountries();
    showCountryList();
  };

  window.getPassCodeWithCountry = function () {
    syncMobileNumber();
    getPassCode();
  };

  window.SMSAuthWithCountry = function () {
    syncMobileNumber();
    SMSAuth();
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initCountrySelector, false);
  } else {
    initCountrySelector();
  }
})();
