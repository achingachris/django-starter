'use strict';
{

    // mock the i18n functions so that javascript code can successfully call
    // them even if translations are disabled.
    // See https://docs.djangoproject.com/en/stable/topics/i18n/translation/#using-the-javascript-translation-catalog

    window.pluralidx = function (count) {
        return (count == 1) ? 0 : 1;
    };
    window.gettext = function (msgid) {
        return msgid;
    };
    window.gettext_noop = function (msgid) {
        return msgid;
    };
    window.ngettext = function (singular, plural, count) {
        return (count == 1) ? singular : plural;
    };
    window.pgettext = function (context, msgid) {
        return msgid;
    };
    window.npgettext = function (context, singular, plural, count) {
        return (count == 1) ? singular : plural;
    };
    window.interpolate = function (fmt, obj, named) {
        if (named) {
            return fmt.replace(/%\(\w+\)s/g, function (match) {
                return String(obj[match.slice(2, -2)])
            });
        } else {
            return fmt.replace(/%s/g, function (match) {
                return String(obj.shift())
            });
        }
    };
}
