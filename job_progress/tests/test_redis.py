import mock
import redis

from job_progress import states
from job_progress.backends.redis import RedisBackend
from job_progress.tests import TEST_SETTINGS


def teardown_function(function):
    # Flush the db.
    _flush_db(TEST_SETTINGS["url"])


def _flush_db(url):
    """Flush a Redis database."""
    client = redis.StrictRedis.from_url(url)
    client.flushdb()


def test_initialize_with_twemproxy():
    """Test that using_twemproxy = True in the RedisBackend
    setting uses a pipeline.
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = False
    redis_backend = RedisBackend(settings)

    redis_backend.client = mock.Mock()
    fake_pipeline = mock.Mock()
    redis_backend.client.pipeline.return_value = fake_pipeline

    redis_backend.initialize_job('my_id', {'my': 'data'}, states.PENDING, 42)

    assert fake_pipeline.execute.called is True


def test_initialize_without_twemproxy():
    """Test that using_twemproxy = False in the RedisBackend
    setting does not use a pipeline.
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)

    redis_backend.client = mock.Mock()
    fake_pipeline = mock.Mock()
    redis_backend.client.pipeline.return_value = fake_pipeline

    redis_backend.initialize_job('my_id', {'my': 'data'}, states.PENDING, 42)

    assert fake_pipeline.execute.called is False


def test_detailed_progress_with_item_id_workflow():
    """Test that add_one_detailed_progress_state will add bject
    to the right states
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis = RedisBackend(settings)
    id = '1'
    s1 = 'SUCCESS'

    redis.add_one_progress_state(id, s1, 'a')
    assert redis.get_detailed_progress_by_state(id, s1) == set(['a'])


def test_get_detailed_progress_by_state_failed_without_state():
    """Test that get_detailed_progress_by_state should return None
    if no state specified
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)

    # Push two value into pending states
    assert redis_backend.get_detailed_progress_by_state('1', None) is None


def test_get_detailed_progress_by_state_does_not_exist():
    """Test that get_detailed_progress_by_state should return empty set
    if state is not existing
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)

    # Push two value into pending states
    assert redis_backend.get_detailed_progress_by_state('1', 'FOO') == set([])
