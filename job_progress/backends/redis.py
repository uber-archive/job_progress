from __future__ import absolute_import
import logging
import redis
import traceback

from job_progress import states
from job_progress.cached_property import cached_property

JOB_LOG_PREFIX = "jobprogress"
INDEX_SUFFIX = "index"
DEFAULT_SETTINGS = {
    "heartbeat_expiration": 3600,  # in seconds
    "using_twemproxy": True,
}


log = logging.getLogger(__name__)


class RedisBackend(object):

    """

    :param dict settings: settings dictionnary
    :param function get_client: function that should return a Redis
        client instance.

    """

    def __init__(self, settings=None, get_client=None):
        self.settings = DEFAULT_SETTINGS.copy()
        if settings:
            self.update_settings(settings)

        self.get_client = get_client

    def call_redis(self, func, *args, **kwargs):
        log_data = {
            'message': 'Updating Redis',
            'function_name': func.__name__,
            'args': args,
            'kwargs': kwargs,
        }

        if func.__name__ == 'delete':
            log_data['tb'] = traceback.format_stack()

        log.info(log_data)

        return func(*args, **kwargs)

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

        if data:
            self.call_redis(self.client.hmset, self._get_metadata_key(key, "data"), data)

        self.call_redis(self.client.set, self._get_metadata_key(key, "amount"), amount)
        self.call_redis(self.client.set, self._get_metadata_key(key, "state"), state)
        self.call_redis(self.client.sadd, self._get_key_for_index("all"), key)
        self.call_redis(self.client.sadd, self._get_key_for_index("state", state), key)

    def delete_job(self, id_, state):
        """Delete a job based on id."""
        key = self._get_key_for_job_id(id_)

        self.call_redis(self.client.delete, self._get_metadata_key(key, "data"))
        self.call_redis(self.client.delete, self._get_metadata_key(key, "amount"))
        self.call_redis(self.client.delete, self._get_metadata_key(key, "state"))
        self.call_redis(self.client.delete, self._get_metadata_key(key, "heartbeat"))
        self.call_redis(self.client.srem, self._get_key_for_index("all"), key)
        self.call_redis(self.client.srem, self._get_key_for_index("state", state), key)

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

        self.call_redis(
            self.client.hincrby,
            self._get_metadata_key(key, "progress"),
            state,
            1,
        )

        self.update_hearbeat(key)

    def update_hearbeat(self, key):
        """Update the task's heartbeat."""
        self.call_redis(
            self.client.setex,
            self._get_metadata_key(key, "heartbeat"),
            self.settings["heartbeat_expiration"],
            1,
        )

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

        self.call_redis(self.client.set, state_key, state)

        # The very last thing is updating the index
        self.update_state_index(key, previous_state, state)

    def update_state_index(self, key, previous_state, new_state):
        """Update the state index."""

        previous_state_key = self._get_key_for_index("state", previous_state)
        new_state_key = self._get_key_for_index("state", new_state)

        if previous_state:
            # This is not an atomic operation
            self.call_redis(self.client.srem, previous_state_key, key)
            self.call_redis(self.client.sadd, new_state_key, key)
        else:
            self.call_redis(self.client.sadd, new_state_key, key)

    def is_staled(self, id_):
        """Return True if job at id_ is staled."""
        key = self._get_key_for_job_id(id_)
        return not bool(self.client.exists(
            self._get_metadata_key(key, "heartbeat")
        ))

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
