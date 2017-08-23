"""
Tests for sneakpeek. Derived from Jason Bau's
Previous Implementation of Direct Access.
Includes modifications introduced by @stvstnfrd
and @vagupta16
"""
from datetime import datetime, timedelta
from django.conf import settings
from django.test import TestCase, RequestFactory
from django.test.utils import override_settings
from django.test import Client
from django.utils.importlib import import_module
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.core.urlresolvers import reverse

from student.models import CourseEnrollment
from student.tests.factories import UserFactory
import courseware.views as views

from ddt import ddt, data
from lazysignup.models import LazyUser
from lazysignup.utils import is_lazy_user
from openedx.stanford.djangoapps.sneakpeek.utils import has_registered
from xmodule.modulestore.tests.factories import CourseFactory
from xmodule.modulestore.tests.django_utils import ModuleStoreTestCase
from middleware import LogoutSneakpeekUsers, LoginSneakpeekUsers
from openedx.stanford.djangoapps.sneakpeek.utils import create_lazy_user


class SneakPeekUserFactory(object):
    """
    create a sneakpeek user that is logged in.
    """
    def create(self, request):
        return create_lazy_user(request)


class TestSneakPeekUser(TestCase):
    """
    Tests the creation of sneakpeek users
    """
    def setUp(self):
        self.request_factory = RequestFactory()
        self.user_factory = SneakPeekUserFactory()
        self.course_id = "course/id/doesnt_matter"

    def test_sneakpeek_userfactory(self):
        dummy_request = self.request_factory.get(self.course_id)
        user = self.user_factory.create(dummy_request)
        self.assertTrue(is_lazy_user(user))

    def test_sneakpeek_progress_404(self):
        with self.assertRaises(Http404):
            request = self.request_factory.get(
                reverse('progress', args=[self.course_id]),
            )
            request.user = self.user_factory.create(request)
            views.progress(request, self.course_id)


NO_SNEAKPEEK_PATHS = [
    '/courses/open/course/run/lti_rest_endpoints/',
    '/courses/open/course/run/xblock/usage_id/handler_noauth/handler',
    '/courses/open/course/run/xqueue/user_id/mod_id/dispatch',
    '/courses/open/course/run/about',
    '/courses/open/course/run/info',
    '/courses/open/course/run/',
]


@ddt
class TestSneakPeekDeepLinking(ModuleStoreTestCase):
    """
    Tests that sneakpeek deep linking middleware, i.e
    LogoutSneakpeekUsers and LoginSneakpeekUsers
    work as expected.
    """
    def setUp(self):
        super(TestSneakPeekDeepLinking, self).setUp()
        self.client = Client()
        self.factory = RequestFactory()
        self.middleware = LoginSneakpeekUsers()
        month = timedelta(days=30)
        month2 = timedelta(days=60)
        now = datetime.now()

        self.nonsneakpeek_course = CourseFactory.create(
            org='nonsneakpeek', number='course',
            run='run', enrollment_start=now - month,
            enrollment_end=now + month,
            allow_sneak_peek=False,
        )
        self.nonsneakpeek_course.save()
        self.open_course = CourseFactory.create(
            org='open', number='course',
            run='run', enrollment_start=now - month,
            enrollment_end=now + month,
            allow_sneak_peek=True,
        )
        self.open_course.save()
        self.closed_course = CourseFactory.create(
            org='closed', number='course',
            run='run', enrollment_start=now - month2,
            enrollment_end=now - month,
            allow_sneak_peek=False,
        )
        self.closed_course.save()
        self.course_to_delete = CourseFactory.create(
            org='deleted', number='course',
            run='run', enrollment_start=now - month,
            enrollment_end=now + month,
            allow_sneak_peek=True,
        )
        self.course_to_delete.save()

    def assertSuccessfulSneakPeek(self, request, course):
        self.assertTrue(is_lazy_user(request.user))
        self.assertFalse(has_registered(request.user))
        self.assertTrue(CourseEnrollment.is_enrolled(request.user, course.id))

    def assertNoSneakPeek(self, request, course, check_auth=True):
        if check_auth:
            self.assertFalse(request.user.is_authenticated())
        self.assertEquals(
            0, CourseEnrollment.objects.filter(course_id=course.id).count()
        )

    def make_successful_sneakpeek_login_request(self):
        sneakpeek_path = '/courses/open/course/run/courseware'
        req = self.factory.get(sneakpeek_path)
        req.session = import_module(settings.SESSION_ENGINE).SessionStore()
        req.user = AnonymousUser()
        return req

    def test_sneakpeek_success(self):
        req = self.make_successful_sneakpeek_login_request()
        self.assertIsNone(self.middleware.process_request(req))
        self.assertSuccessfulSneakPeek(req, self.open_course)

    def test_non_get(self):
        req = self.make_successful_sneakpeek_login_request()
        req.method = "POST"
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.open_course)

    def test_get_404(self):
        req = self.make_successful_sneakpeek_login_request()
        req.path = '/foobarmew'
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.open_course)

    @data(*NO_SNEAKPEEK_PATHS)
    def test_url_blacklists(self, path):
        req = self.make_successful_sneakpeek_login_request()
        req.path = path
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.open_course)

    def test_authenticated_user(self):
        req = self.make_successful_sneakpeek_login_request()
        user = UserFactory()
        user.save()
        req.user = user
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.open_course, check_auth=False)

    def test_noncourse_path(self):
        req = self.make_successful_sneakpeek_login_request()
        req.path = "/dashboard"
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.open_course)

    def test_nonsneakpeek_course(self):
        req = self.make_successful_sneakpeek_login_request()
        req.path = '/courses/nonsneakpeek/course/run/info'
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.nonsneakpeek_course)

    def test_sneakpeek_course_enrollment_closed(self):
        req = self.make_successful_sneakpeek_login_request()
        req.path = '/courses/closed/course/run/info'
        self.assertIsNone(self.middleware.process_request(req))
        self.assertNoSneakPeek(req, self.closed_course)

    def test_deleted_course_with_preferences(self):
        """
        Verify that Sneakpeek requests fail after deleting a course
        """
        request = self.make_successful_sneakpeek_login_request()
        request.path = '/courses/deleted/course/run/courseware'
        self.assertIsNone(self.middleware.process_request(request))
        self.assertSuccessfulSneakPeek(request, self.course_to_delete)
        self.store.delete_course(self.course_to_delete.id, self.user)
        request = self.make_successful_sneakpeek_login_request()
        request.path = '/courses/deleted/course/run/courseware'
        self.assertIsNone(self.middleware.process_request(request))
        self.assertFalse(request.user.is_authenticated())
        count = CourseEnrollment.objects.filter(course_id=self.course_to_delete.id).count()
        self.assertEquals(1, count)
