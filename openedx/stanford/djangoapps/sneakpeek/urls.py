"""
URLS for sneakpeek.
"""
from django.conf.urls import patterns, url, include

urlpatterns = (
    url(r'^convert/', include('lazysignup.urls')),
    url(
        r'^course_sneakpeek/{}/$'.format(settings.COURSE_ID_PATTERN),
        'openedx.stanford.djangoapps.sneakpeek.views.setup_sneakpeek',
        name='course_sneakpeek',
    ),
)
