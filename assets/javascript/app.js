import * as JsCookie from "js-cookie";
import { getCsrfToken } from './csrf';

export { getCsrfToken };
export const Cookies = JsCookie.default;

// Ensure SiteJS global exists
if (typeof window.SiteJS === 'undefined') {
  window.SiteJS = {};
}

// Assign this entry's exports to SiteJS.app
window.SiteJS.app = {
  Cookies: JsCookie.default,
  getCsrfToken,
};
