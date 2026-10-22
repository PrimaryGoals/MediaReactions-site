/* Keeps the footer's copyright year current without a rebuild. */
(function () {
  var year = String(new Date().getFullYear());
  Array.prototype.forEach.call(document.querySelectorAll('.current-year'), function (el) { el.textContent = year; });
})();

/* Contact form: send in the background and go to the thank-you page without waiting for FormSubmit's slow
   redirect. Without JavaScript the form still posts normally. */
document.addEventListener('submit', function (e) {
  var form = e.target;
  if (!form.action || form.action.indexOf('https://formsubmit.co/') !== 0) { return; }
  e.preventDefault();

  var data = {};
  Array.prototype.forEach.call(form.elements, function (el) {
    if (el.name && el.type !== 'submit' && el.type !== 'button') { data[el.name] = el.value; }
  });
  var next = data._next || '/';
  var button = form.querySelector('button[type=submit]');
  var label = button && button.querySelector('.text');
  if (button) { button.disabled = true; }
  if (label) { label.textContent = 'Sending…'; }

  var done = false;
  function go() { if (!done) { done = true; window.location.href = next; } }
  function fallback() {  // something went wrong: let the browser post the form the normal way
    if (done) { return; }
    done = true;
    HTMLFormElement.prototype.submit.call(form);
  }

  // The request keeps running after the page changes (keepalive), so a short wait is enough.
  setTimeout(go, 3000);
  fetch(form.action.replace('https://formsubmit.co/', 'https://formsubmit.co/ajax/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify(data),
    keepalive: true
  }).then(function (r) { return r.json(); }).then(function (j) {
    if (j && (j.success === true || j.success === 'true')) { go(); } else { fallback(); }
  }).catch(fallback);
});

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
