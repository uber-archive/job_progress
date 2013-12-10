from __future__ import absolute_import
import uuid

from job_progress import states


def _generate_id():
    """Return job unique id."""
    return str(uuid.uuid4())


class JobProgress(object):

    backend = None
    session = None

    def __init__(self, data, amount, id_=None, state=None,
                 previous_state=None):
        self.data = data
        self.amount = amount
        state = state or states.PENDING
        self._previous_state = previous_state or states.PENDING

        if id_:
            # Loading from db
            self.id = id_

        else:
            # Store in the back-end
            self.id = _generate_id()
            self.backend.initialize_job(self.id, self.data, state,
                                        self.amount)
            self.session.add(self.id, self)

    @classmethod
    def from_backend(cls, data, amount, id_, state, previous_state):
        """Load from backend."""

        self = cls(data, amount, id_, state, previous_state)
        return self

    @property
    def backend(self):
        """Return backend instance."""
        return self.backend_factory()

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
            }
        """
        return self.backend.get_progress(self.id)

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
