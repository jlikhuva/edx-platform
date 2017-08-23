"""
Handles lazily signed in users, aka sneakpeek users
in studio (i.e cms). Long story short, it
prevents them from accessing studio.
"""
import logging

from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth import authenticate
from django.core.urlresolvers import resolve
from django.http import Http404

from util.request import course_id_from_url
from student.views import _check_can_enroll_in_course
from student.models import CourseEnrollment
from xmodule.modulestore.django import modulestore

from lazysignup.utils import is_lazy_user
from openedx.stanford.djangoapps.sneakpeek.utils import create_lazy_user

DISALLOW_SNEAKPEEK_URL_NAMES = (
    'lti_rest_endpoints',
    'xblock_handler_noauth',
    'xqueue_callback',
    'about_course',
    'course_root',
    'info',
)
LOG = logging.getLogger('edx.sneakpeek_middleware')


class LogoutSneakpeekUsers(object):
    """
    Prevents sneak-peek users from accessing studio
    by logging them out and re-sending the request without
    them being logged in.
    """
    def process_request(self, request):
        if is_lazy_user(request.user):
            logout(request)
            return redirect(
                request.get_full_path()
            )
        return None


class LoginSneakpeekUsers(object):
    """
    Middleware class that supports deep-links
    for courses that allow sneakpeek.
    The user will be registered anonymously,
    logged in, and enrolled in the course.
    """
    def process_request(self, request):
        if request.method != 'GET':
            return None

        try:
            match = resolve(request.path)
            if match.url_name in DISALLOW_SNEAKPEEK_URL_NAMES:
                return None
        except Http404:
            pass

        if request.user.is_authenticated():
            return None

        course_id = course_id_from_url(request.path)
        if not course_id:
            return None

        if not modulestore().has_course(course_id):
            message = u'Sneakpeek attempt for non-existent course %s'
            LOG.warning(message, course_id)
            return None

        if not modulestore().get_course(course_id).allow_sneak_peek:
            return None

        can_enroll, _ = _check_can_enroll_in_course(
            request.user,
            course_id,
            access_type='within_enrollment_period'
        )
        if not can_enroll:
            return None

        """
        OK. Now, create an anonymous user, log them in, and enroll them
        in the course.
        """
        user = create_lazy_user(request)
        CourseEnrollment.enroll(request.user, course_id)
        return None
