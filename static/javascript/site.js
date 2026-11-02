// Site-wide JavaScript, loaded as a plain script from templates/web/base.html.
// htmx and Alpine.js are loaded separately from static/vendor/.
(function () {
  'use strict';

  // --- CSRF -----------------------------------------------------------------
  // The CSRF cookie name is provided by the server (Django's CSRF_COOKIE_NAME,
  // rendered into a <meta> tag by base.html) so the front end always reads the
  // right cookie even when the name is customized. Falls back to Django's
  // default if the meta tag is missing. Every caller should go through
  // SiteJS.getCsrfToken() rather than hardcoding the cookie name.
  const csrfCookieName = () =>
    document.querySelector('meta[name="csrf-cookie-name"]')?.content || 'csrftoken';

  const getCookie = (name) => {
    const match = document.cookie
      .split('; ')
      .find((row) => row.startsWith(name + '='));
    return match ? decodeURIComponent(match.slice(name.length + 1)) : undefined;
  };

  const getCsrfToken = () => getCookie(csrfCookieName());

  window.SiteJS = { getCsrfToken };

  // --- i18n mocks -------------------------------------------------------------
  // Mock the Django JavaScript i18n functions so code can call them even when
  // translations are disabled.
  // https://docs.djangoproject.com/en/stable/topics/i18n/translation/#using-the-javascript-translation-catalog
  window.pluralidx = (count) => (count == 1 ? 0 : 1);
  window.gettext = (msgid) => msgid;
  window.gettext_noop = (msgid) => msgid;
  window.ngettext = (singular, plural, count) => (count == 1 ? singular : plural);
  window.pgettext = (context, msgid) => msgid;
  window.npgettext = (context, singular, plural, count) => (count == 1 ? singular : plural);
  window.interpolate = (fmt, obj, named) => {
    if (named) {
      return fmt.replace(/%\(\w+\)s/g, (match) => String(obj[match.slice(2, -2)]));
    }
    return fmt.replace(/%s/g, () => String(obj.shift()));
  };

  // --- Logout links -----------------------------------------------------------
  // Convert clicks on logout links into one-click POST submissions, skipping
  // allauth's confirmation page. Links opt in with `data-logout-link` rather
  // than matching a hardcoded URL, so this stays decoupled from the logout path.
  // Falls back to the confirmation page when JS is disabled.
  document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('a[data-logout-link]').forEach((link) => {
      link.addEventListener('click', (e) => {
        e.preventDefault();
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = link.getAttribute('href');

        const csrf = document.createElement('input');
        csrf.type = 'hidden';
        csrf.name = 'csrfmiddlewaretoken';
        csrf.value = getCsrfToken();
        form.appendChild(csrf);

        document.body.appendChild(form);
        form.submit();
      });
    });
  });

  // --- PWA --------------------------------------------------------------------
  // Register the offline-caching service worker.
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js').catch((err) => {
        console.warn('Service worker registration failed:', err);
      });
    });
  }

  // Custom "Install App" prompt, using the browser's beforeinstallprompt event
  // so the app can be added to the home screen.
  let deferredInstallPrompt = null;

  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    const installButton = document.getElementById('pwa-install-button');
    if (installButton) {
      installButton.classList.remove('hidden');
    }
  });

  document.addEventListener('click', (event) => {
    if (event.target && event.target.id === 'pwa-install-button') {
      if (!deferredInstallPrompt) return;
      deferredInstallPrompt.prompt();
      deferredInstallPrompt.userChoice.finally(() => {
        deferredInstallPrompt = null;
        event.target.classList.add('hidden');
      });
    }
  });

  window.addEventListener('appinstalled', () => {
    const installButton = document.getElementById('pwa-install-button');
    if (installButton) {
      installButton.classList.add('hidden');
    }
  });
})();
