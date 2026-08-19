"""utm_source/medium/campaign travel with a page load, not a form post — so
every public template renders them as hidden fields (see
`components/utm_fields.html`) seeded from the *page's* querystring, and every
form-handling view reads them back from POST like any other field."""

UTM_PARAMS = ("utm_source", "utm_medium", "utm_campaign")


def utm_initial(request):
    return {param: request.GET.get(param, "") for param in UTM_PARAMS}
