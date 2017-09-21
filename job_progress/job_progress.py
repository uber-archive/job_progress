from __future__ import absolute_import
import uuid

from job_progress import states
from job_progress.utils import classproperty


def _generate_id():
    """Return job unique id."""
    return str(uuid.uuid4())


class JobProgress(object):

    """
    JobProgress

    :param int amount: amount of work to do.
    :param dict data: metadata about the job.
    :param str id_: job identifier
    :param str state: state the job starts with
    :param str previous_state:
    :param bool loading:

    """

    session = None

    def __init__(self, data=None, amount=1, id_=None, state=states.PENDING,
                 previous_state=states.PENDING, loading=False):
        self.data = data or {}
        self.amount = amount
        self._previous_state = previous_state
        self.id = id_ or _generate_id()
        self.delete_on_closing = False

        if not loading:
            # Store in the back-end
            self.backend.initialize_job(self.id, self.data, state,
                                        self.amount)
            self.session.add(self.id, self)

    def __repr__(self):
        """Return repr of the object."""
        return "<%s '%s'>" % (self.__class__.__name__, self.id)

    @classmethod
    def from_backend(cls, data, amount, id_, state, previous_state):
        """Load from backend."""
        self = cls(data, amount, id_, state, previous_state, loading=True)
        return self

    @classmethod
    def query(cls, **filters):
        """Query the backend.

        :param filters: filters.

        Currently supported filters are:

        - ``is_ready``
        - ``state``

        This method should be considered alpha.
        """

        ids = cls.backend.get_ids(**filters)
        return [cls.session.get(id_) for id_ in ids]

    @classmethod
    def set_session(cls, session):
        """Set the session."""
        cls.session = session

    @classproperty
    def backend(cls):
        """Return backend instance."""
        return cls.session.backend

    @property
    def is_ready(self):
        """Return True if is ready."""
        return self.state in states.READY_STATES

    @property
    def state(self):
        """Return state."""
        return self.backend.get_state(self.id)

    @state.setter  # noqa
    def state(self, state):
        """Set the state."""
        self.backend.set_state(self.id, state, self._previous_state)
        self._previous_state = state

    @property
    def is_staled(self):
        """Return True if staled."""
        return self.state == states.STARTED and self.backend.is_staled(self.id)

    def run(self, delete_on_closing=False):
        """Return a context manager.

        :param bool delete: if ``True``, will delete on closing.
        """
        self.delete_on_closing = delete_on_closing
        return self

    def __enter__(self):
        """Enter the context manager."""
        self.state = states.STARTED
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        if exc_value:
            self.state = states.FAILURE
        else:
            self.state = states.SUCCESS
        if self.delete_on_closing:
            self.delete()

    def add_one_progress_state(self, state):
        """Add one unit status."""
        return self.backend.add_one_progress_state(self.id, state)

    def add_one_failure(self):
        """Add one failure state."""
        return self.add_one_progress_state(states.FAILURE)

    def add_one_success(self):
        """Add one success state."""
        return self.add_one_progress_state(states.SUCCESS)

    def get_progress(self):
        """Return the progress.

        :rtype: dict

        E.g.::

            {
            "success": 12,
            "failure": 14,
            "pending": 32,
            }
        """
        progress = self.backend.get_progress(self.id)
        progress = {k: int(v) for k, v in progress.items()}

        pending = 0
        if self.amount:
            # There can be a race condition before we have saved amount.
            pending = int(self.amount) - sum(progress.values())

        progress[states.PENDING] = pending

        return progress

    def to_dict(self):
        """Return dict representation of the object."""
        returned = {
            "id": self.id,
            "data": self.data,
            "amount": self.amount,
            "progress": self.get_progress(),
            "is_ready": self.is_ready,
            "state": self.state,
        }
        return returned

    def delete(self):
        """Delete the job."""
        self.backend.delete_job(self.id, self.state)
