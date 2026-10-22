/* Keeps the footer's copyright year current without a rebuild. */
(function () {
  var year = String(new Date().getFullYear());
  Array.prototype.forEach.call(document.querySelectorAll('.current-year'), function (el) { el.textContent = year; });
})();

/* Opens the contact form pop-up on the landing pages (replaces the OptimizePress pop-up script). */
(function () {
  var links = document.querySelectorAll('a.css-button');
  Array.prototype.forEach.call(links, function (a) {
    // the pop-up content follows the button, or follows one of the button's wrapper elements
    var content = null;
    for (var node = a, depth = 0; node && !content && depth < 5; node = node.parentNode, depth++) {
      var next = node.nextElementSibling;
      if (next && next.classList.contains('op-popup-content')) { content = next; }
    }
    if (!content) { return; }

    a.addEventListener('click', function (e) {
      e.preventDefault();
      var overlay = document.createElement('div');
      overlay.className = 'mr-modal';
      overlay.setAttribute('role', 'dialog');
      overlay.setAttribute('aria-modal', 'true');
      overlay.innerHTML = '<div class="mr-modal-box"><button type="button" class="mr-modal-close" aria-label="Close">&times;</button><div class="mr-modal-body"></div></div>';
      overlay.querySelector('.mr-modal-body').innerHTML = content.innerHTML;
      function close() {
        document.removeEventListener('keydown', onKey);
        overlay.parentNode.removeChild(overlay);
        a.focus();
      }
      function onKey(ev) { if (ev.key === 'Escape') { close(); } }
      overlay.addEventListener('click', function (ev) {
        if (ev.target === overlay || ev.target.className === 'mr-modal-close') { close(); }
      });
      document.addEventListener('keydown', onKey);
      document.body.appendChild(overlay);
      var first = overlay.querySelector('input[type=text], input[type=email]');
      if (first) { first.focus(); }
    });
  });
})();
