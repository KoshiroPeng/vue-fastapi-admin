(function () {
  var messageTimer;

  function showMessage(text, type) {
    var message = document.getElementById("infoMsg");
    var messageBox = document.getElementById("infoMsgBox");
    var messageIcon = document.getElementById("msgIcon");
    var messageText = document.getElementById("msgText");
    var isSuccess = type !== "error";

    if (!message || !messageBox || !messageIcon || !messageText) {
      return;
    }

    window.clearTimeout(messageTimer);
    messageBox.className = isSuccess ? "successInfoMsgBox" : "errorInfoMsgBox";
    messageIcon.src = isSuccess ? "assets/check.svg" : "assets/close.png";
    messageText.innerText = text;
    message.style.display = "flex";
    messageTimer = window.setTimeout(function () {
      message.style.display = "none";
    }, 3000);
  }

  function copyWithLegacyApi(text) {
    var activeElement = document.activeElement;
    var textarea = document.createElement("textarea");
    var copied = false;

    textarea.value = text;
    textarea.setAttribute("readonly", "readonly");
    textarea.style.position = "fixed";
    textarea.style.top = "0";
    textarea.style.left = "-9999px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, textarea.value.length);

    try {
      copied = document.execCommand("copy");
    } catch (_error) {
      copied = false;
    }

    document.body.removeChild(textarea);
    if (activeElement && typeof activeElement.focus === "function") {
      activeElement.focus();
    }
    return copied;
  }

  function showCopyResult(copied) {
    showMessage(
      copied ? "{{passport.copySuccess}}" : "{{passport.copyFailed}}",
      copied ? "success" : "error"
    );
  }

  window.showMessage = showMessage;
  window.copyToClipboard = function () {
    var text = window.location.href;

    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        navigator.clipboard.writeText(text).then(
          function () {
            showCopyResult(true);
          },
          function () {
            showCopyResult(copyWithLegacyApi(text));
          }
        );
        return;
      } catch (_error) {
        showCopyResult(copyWithLegacyApi(text));
        return;
      }
    }

    showCopyResult(copyWithLegacyApi(text));
  };
})();
