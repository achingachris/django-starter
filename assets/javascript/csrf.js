import Cookies from 'js-cookie';

// The CSRF cookie name is provided by the server (Django's CSRF_COOKIE_NAME,
// rendered into a <meta> tag by base.html) so the front end always reads the
// right cookie even when the name is customized. Falls back to Django's
// default if the meta tag is missing. Every caller should go through
// getCsrfToken() rather than hardcoding the cookie name.
const csrfCookieName = () =>
  document.querySelector('meta[name="csrf-cookie-name"]')?.content || 'csrftoken';

export const getCsrfToken = () => Cookies.get(csrfCookieName());
