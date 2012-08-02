from itertools import repeat

from xmodule.course_module import CourseDescriptor

from .exceptions import (ItemNotFoundError, NoPathToItem)
from . import ModuleStore, Location


def path_to_location(modulestore, location, course_name=None):
    '''
    Try to find a course_id/chapter/section[/position] path to location in
    modulestore.  The courseware insists that the first level in the course is
    chapter, but any kind of module can be a "section".

    location: something that can be passed to Location
    course_name: [optional].  If not None, restrict search to paths
        in that course.

    raise ItemNotFoundError if the location doesn't exist.

    raise NoPathToItem if the location exists, but isn't accessible via
    a chapter/section path in the course(s) being searched.

    Return a tuple (course_id, chapter, section, position) suitable for the
    courseware index view.

    A location may be accessible via many paths. This method may
    return any valid path.

    If the section is a sequence, position will be the position
    of this location in that sequence.  Otherwise, position will
    be None. TODO (vshnayder): Not true yet.
    '''

    def flatten(xs):
        '''Convert lisp-style (a, (b, (c, ()))) list into a python list.
        Not a general flatten function. '''
        p = []
        while xs != ():
            p.append(xs[0])
            xs = xs[1]
        return p

    def find_path_to_course(location, course_name=None):
        '''Find a path up the location graph to a node with the
        specified category.

        If no path exists, return None.

        If a path exists, return it as a list with target location first, and
        the starting location last.
        '''
        # Standard DFS

        # To keep track of where we came from, the work queue has
        # tuples (location, path-so-far).  To avoid lots of
        # copying, the path-so-far is stored as a lisp-style
        # list--nested hd::tl tuples, and flattened at the end.
        queue = [(location, ())]
        while len(queue) > 0:
            (loc, path) = queue.pop()  # Takes from the end
            loc = Location(loc)

            # get_parent_locations should raise ItemNotFoundError if location
            # isn't found so we don't have to do it explicitly.  Call this
            # first to make sure the location is there (even if it's a course, and
            # we would otherwise immediately exit).
            parents = modulestore.get_parent_locations(loc)

            # print 'Processing loc={0}, path={1}'.format(loc, path)
            if loc.category == "course":
                if course_name is None or course_name == loc.name:
                    # Found it!
                    path = (loc, path)
                    return flatten(path)

            # otherwise, add parent locations at the end
            newpath = (loc, path)
            queue.extend(zip(parents, repeat(newpath)))

        # If we're here, there is no path
        return None

    path = find_path_to_course(location, course_name)
    if path is None:
        raise(NoPathToItem(location))

    n = len(path)
    course_id = CourseDescriptor.location_to_id(path[0])
    chapter = path[1].name if n > 1 else None
    section = path[2].name if n > 2 else None

    # TODO (vshnayder): not handling position at all yet...
    position = None

    return (course_id, chapter, section, position)
