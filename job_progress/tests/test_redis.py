import mock

import pytest

from job_progress import states
from job_progress.backends.redis import RedisBackend
from job_progress.tests import TEST_SETTINGS


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


def test_update_object_state():
    """
    Test that update_object_state will move object
    to the right bucket
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)
    progress_id = RedisBackend._get_key_for_job_id('1')
    pending_key = RedisBackend._get_metadata_key(progress_id, "info:pending")
    success_key = RedisBackend._get_metadata_key(progress_id, "info:success")

    # Push two object into pending bucket
    redis_backend.update_object_state('1', None, 'pending', '12')
    redis_backend.update_object_state('1', None, 'pending', 'abc')
    assert redis_backend.client.smembers(pending_key) == set(['12', 'abc'])

    # Move the first object into success bucket
    redis_backend.update_object_state('1', 'pending', 'success', '12')
    assert redis_backend.client.smembers(success_key) == set(['12'])
    assert redis_backend.client.smembers(pending_key) == set(['abc'])

    redis_backend.client.flushdb()


def test_update_object_state_failed_without_to_state():
    """
    Test that update_object_state should raise ValueError
    if to_state is falsy
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)

    with pytest.raises(ValueError):
        redis_backend.update_object_state('1', None, None, '123')

    redis_backend.client.flushdb()


def test_get_objects_by_state():
    """
    Test that get_objects_by_state should return all objects
    in that state
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)
    progress_id = RedisBackend._get_key_for_job_id('1')
    pending_key = RedisBackend._get_metadata_key(progress_id, "info:pending")

    # Push two object into pending bucket
    redis_backend.update_object_state('1', None, 'pending', '12')
    redis_backend.update_object_state('1', None, 'pending', 'abc')
    assert (redis_backend.get_objects_by_state('1', 'pending')
            == set(['12', 'abc']))

    redis_backend.client.flushdb()


def test_get_objects_by_state_failed_without_state():
    """
    Test that get_objects_by_state should return empty set
    if no state specified
    """
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)

    # Push two object into pending bucket
    assert redis_backend.get_objects_by_state('1', None) is None

    redis_backend.client.flushdb()
