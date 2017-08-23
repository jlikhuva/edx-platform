from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.utils.importlib import import_module
from django.conf import settings
from django.contrib.auth import SESSION_KEY

from lazysignup.decorators import is_lazy_user
from lazysignup.models import LazyUser

from openedx.stanford.lms.envs.common import NONREGISTERED_CATEGORY_WHITELIST


def _can_load_descriptor_sneakpeek(descriptor):
    return descriptor.category in NONREGISTERED_CATEGORY_WHITELIST


def has_registered(user):
    """
    Checks that the user is neither a django AnonymousUser
    nor a lazysignup sneakpeek/lazy user.
    """
    return user.is_authenticated() and not is_lazy_user(user)


def is_sneakpeek_allowed(user, course, course_key):
    """
    sneakpeek is allowed if:
        1. We're within the enrollment period
        2. Course allows lazy users
        3. request.user is not a registered user.
    """
    from lms.djangoapps.courseware.access import has_access

    if not has_access(user, 'within_enrollment_period', course):
        return False
    if not course.allow_sneak_peek:
        return False
    if has_registered(user):
        return False
    return True


def create_lazy_user(request):
    """
    Create a lazy user and log them in.
    """
    user, username = LazyUser.objects.create_lazy_user()
    request.user = None
    user = authenticate(username=username)
    request.session = import_module(settings.SESSION_ENGINE).SessionStore()
    request.session[SESSION_KEY] = user.id
    login(request, user)
    return user
