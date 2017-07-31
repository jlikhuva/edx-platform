"""
Handles lazily signed in users, aka sneakpeek users
in studio (i.e cms). Long story short, it
prevents them from accessing studio.
"""

from lazysignup.utils import is_lazy_user
from django.shortcuts import redirect
from django.contrib.auth import logout


class BlockSneakpeekUsers(object):
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
        else:
            return None


