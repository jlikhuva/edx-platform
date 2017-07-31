from cms.envs.test import *


FEATURES['ALLOW_COURSE_RERUNS'] = True
INSTALLED_APPS += (
    'openedx.stanford.djangoapps.register_cme',
)

MIDDLEWARE_CLASSES = tuple([
    c for c in MIDDLEWARE_CLASSES
    if c != 'openedx.stanford.djangoapps.sneakpeek.middleware.BlockSneakpeekUsers'
])
