from __future__ import absolute_import
import redis

from job_progress import states
from job_progress.cached_property import cached_property

JOB_LOG_PREFIX = "jobprogress"
INDEX_SUFFIX = "index"
DEFAULT_SETTINGS = {
    "heartbeat_expiration": 3600,  # in seconds
    "using_twemproxy": True,
}


class RedisBackend(object):

    """

    :param dict settings: settings dictionnary
    :param function get_client: function that should return a Redis
        client instance.

    """

    def __init__(self, settings=None, get_client=None):
        self.settings = DEFAULT_SETTINGS.copy()
        if settings:
            self.settings.update(settings)

        self.get_client = get_client

    def update_settings(self, settings):
        """Update the settings.

        :param dict settings:
        """
        self.settings.update(settings)

    @cached_property
    def client(self):
        """Return Redis client."""
        if self.get_client:
            return self.get_client()
        else:
            return redis.StrictRedis.from_url(self.settings["url"])

    def initialize_job(self, id_,
                       data, state, amount):
        """Initialize and store a job."""
        key = self._get_key_for_job_id(id_)

        using_twemproxy = self.settings.get('using_twemproxy')
        client = self.client.pipeline() if not using_twemproxy else self.client

        if data:
            client.hmset(self._get_metadata_key(key, "data"), data)
        client.set(self._get_metadata_key(key, "amount"), amount)
        client.set(self._get_metadata_key(key, "state"), state)
        client.sadd(self._get_key_for_index("all"), key)
        client.sadd(self._get_key_for_index("state", state), key)
        if not using_twemproxy:
            client.execute()

    def delete_job(self, id_, state):
        """Delete a job based on id."""
        key = self._get_key_for_job_id(id_)

        using_twemproxy = self.settings.get('using_twemproxy')
        client = self.client.pipeline() if not using_twemproxy else self.client

        client.delete(self._get_metadata_key(key, "data"))
        client.delete(self._get_metadata_key(key, "amount"))
        client.delete(self._get_metadata_key(key, "state"))
        client.delete(self._get_metadata_key(key, "heartbeat"))
        client.srem(self._get_key_for_index("all"), key)
        client.srem(self._get_key_for_index("state", state), key)
        if not using_twemproxy:
            client.execute()

    def get_data(self, id_):
        """Return data for a given job."""
        key = self._get_key_for_job_id(id_)
        client = self.client

        data = client.hgetall(self._get_metadata_key(key, "data"))
        amount = client.get(self._get_metadata_key(key, "amount"))
        state = client.get(self._get_metadata_key(key, "state"))

        return {
            "data": data,
            "amount": amount,
            "state": state,
            "previous_state": state,
        }

    def add_one_progress_state(self, id_, state):
        """Add one unit state."""
        key = self._get_key_for_job_id(id_)
        self.client.hincrby(self._get_metadata_key(key, "progress"),
                            state, 1)
        self.update_hearbeat(key)

    def update_hearbeat(self, key):
        """Update the task's heartbeat."""
        self.client.setex(self._get_metadata_key(key, "heartbeat"),
                          self.settings["heartbeat_expiration"],
                          1)

    def get_progress(self, id_):
        """Return progress."""
        key = self._get_key_for_job_id(id_)
        states_key = self._get_metadata_key(key, "progress")
        return self.client.hgetall(states_key)

    def get_state(self, id_):
        """Return state of a given id."""
        key = self._get_key_for_job_id(id_)
        state_key = self._get_metadata_key(key, "state")
        return self.client.get(state_key)

    def set_state(self, id_, state, previous_state=None):
        """Set state of a given id."""
        key = self._get_key_for_job_id(id_)

        # The first thing we do is update the heartbeat to prevent any
        # race condition
        if state == states.STARTED:
            self.update_hearbeat(key)

        # First set the state
        state_key = self._get_metadata_key(key, "state")
        self.client.set(state_key, state)

        # The very last thing is updating the index
        self.update_state_index(key, previous_state, state)

    def update_state_index(self, key, previous_state, new_state):
        """Update the state index."""

        previous_state_key = self._get_key_for_index("state", previous_state)
        new_state_key = self._get_key_for_index("state", new_state)

        if previous_state:
            # This is an atomic operation.
            self.client.smove(previous_state_key, new_state_key, key)
        else:
            self.client.sadd(new_state_key, key)

    def is_staled(self, id_):
        """Return True if job at id_ is staled."""
        key = self._get_key_for_job_id(id_)
        return not bool(self.client.exists(key))

    @classmethod
    def _get_key_for_job_id(cls, id_):
        """Return a Redis key based on an id."""
        return "{}:{}".format(JOB_LOG_PREFIX, id_)

    @classmethod
    def _get_key_for_index(cls, index_name, value=None):
        """Return a Redis key based on the index_name and value."""
        return "{}:{}:{}:{}".format(JOB_LOG_PREFIX,
                                    index_name,
                                    INDEX_SUFFIX,
                                    value)

    @classmethod
    def _get_metadata_key(cls, key, name):
        """Return metadata key.

        :param str key:
        :param str name:
        """
        return "{}:{}".format(key, name)

    def get_ids(self, **filters):
        """Query the backend.

        :param filters: filters.

        Currently supported filters are:

        - ``is_ready``
        - ``state``
        """

        if filters:
            keys = []

            if "is_ready" in filters:
                is_ready = filters.pop("is_ready")

                if is_ready is False:
                    searched_states = states.NOT_READY_STATES
                elif is_ready is True:
                    searched_states = states.READY_STATES
                else:
                    raise TypeError("Unknown is_ready type: '%r'" % is_ready)

                # We need to get all the ids

                if not self.settings.get('using_twemproxy'):
                    keys.extend(self.client.sunion(
                        self._get_key_for_index("state", state)
                        for state in searched_states))
                else:
                    # twemproxy does not support sunion.
                    ids = set()

                    for state in searched_states:
                        ids.update(self.client.smembers(
                            self._get_key_for_index("state", state)
                        ))

                    keys.extend(ids)

            if "state" in filters:
                state = filters.pop("state")
                keys.extend(self.client.smembers(
                    self._get_key_for_index("state", state)))

            if filters:
                raise TypeError("Unknown filters: %s" % filters)

        else:
            # Just get all keys
            keys = self.client.smembers(self._get_key_for_index("all"))

        return [key.split(":")[1] for key in keys]
