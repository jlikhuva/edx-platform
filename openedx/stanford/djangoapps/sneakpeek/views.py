from django.shortcuts import render
from opaque_keys.edx.locations import SlashSeparatedCourseKey
from student.models import CourseEnrollment
from django.http import HttpResponse
from lazysignup.decorators import allow_lazy_user
from django.views.decorators.http import require_POST

@allow_lazy_user
@require_POST
def setup_sneakpeek(request, course_id):
    key = SlashSeparatedCourseKey.from_deprecated_string(course_id)
    CourseEnrollment.enroll(request.user, key)
    return HttpResponse("OK. sneakpeek successfull")
