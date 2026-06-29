import {getCsrfToken} from "./csrf";

// Convert clicks on logout links into one-click POST submissions, skipping
// allauth's confirmation page. Links opt in with `data-logout-link` rather
// than matching a hardcoded URL, so this stays decoupled from the logout path.
// Falls back to the confirmation page when JS is disabled.
document.addEventListener("DOMContentLoaded", () => {
  const links = document.querySelectorAll("a[data-logout-link]");
  links.forEach((link) => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const form = document.createElement("form");
      form.method = "POST";
      form.action = link.getAttribute("href");

      const csrf = document.createElement("input");
      csrf.type = "hidden";
      csrf.name = "csrfmiddlewaretoken";
      csrf.value = getCsrfToken();
      form.appendChild(csrf);

      document.body.appendChild(form);
      form.submit();
    });
  });
});
