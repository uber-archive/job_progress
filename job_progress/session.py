from __future__ import absolute_import
import weakref

from job_progress.job_progress import JobProgress


class Session(object):

    """
    The Session object mimics sqlalchemy's session, but does caching
    so that we don't reload an object.
    """

    def __init__(self, backend):
        self.objects = self._new_cache_storage()
        self.backend = backend
        self.job_progress_class = JobProgress

    def get(self, id_):
        """Get an object from the backend."""

        obj = self.objects.get(id_)
        if obj:
            return obj

        # Get the data from the backend
        data = self.backend.get_data(id_)
        # Instantiate the object
        obj = self.job_progress_class.from_backend(id_=id_, **data)
        # Add it to the cache
        self.add(id_, obj)

        return obj

    def add(self, id_, obj):
        """Add an object in the session."""
        self.objects[id_] = obj

    def clear(self):
        """Clear the cache."""
        self.objects = self._new_cache_storage()

    def _new_cache_storage(self):
        return weakref.WeakValueDictionary()

    def query(self, **filters):
        """Query the backend.

        :param filters: filters.

        Currently supported filters are:

        - ``is_ready``
        - ``state``

        This method should be considered alpha.
        """

        ids = self.backend.get_ids(**filters)
        return [self.get(id_) for id_ in ids]
