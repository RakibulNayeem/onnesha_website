/* Day / night mode.
   Loaded synchronously from <head> so the theme is set before the first
   paint - a deferred script would show a flash of the wrong one. */
(function () {
  var KEY = 'onnesha-theme';
  var root = document.documentElement;

  function preferred() {
    try {
      var saved = localStorage.getItem(KEY);
      if (saved === 'dark' || saved === 'light') return saved;
    } catch (e) { /* private window, blocked storage */ }
    return window.matchMedia &&
      window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function apply(mode) {
    root.setAttribute('data-bs-theme', mode);
    var dark = mode === 'dark';
    var label = dark ? 'Switch to day mode' : 'Switch to night mode';
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    for (var i = 0; i < buttons.length; i++) {
      var icon = buttons[i].querySelector('i');
      if (icon) icon.className = 'bi bi-' + (dark ? 'sun' : 'moon-stars');
      buttons[i].setAttribute('aria-label', label);
      buttons[i].setAttribute('title', label);
    }
  }

  apply(preferred());

  document.addEventListener('DOMContentLoaded', function () {
    apply(root.getAttribute('data-bs-theme'));  // the buttons exist now
    var buttons = document.querySelectorAll('[data-theme-toggle]');
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].addEventListener('click', function () {
        var next = root.getAttribute('data-bs-theme') === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem(KEY, next); } catch (e) {}
        apply(next);
      });
    }
  });

  // Receipts and reports go onto white paper whatever the screen is doing.
  window.addEventListener('beforeprint', function () {
    root.setAttribute('data-bs-theme', 'light');
  });
  window.addEventListener('afterprint', function () {
    apply(preferred());
  });
})();
