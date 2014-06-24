import redis
import mock

from job_progress import states
from job_progress.backends.redis import RedisBackend
from job_progress.tests import TEST_SETTINGS


def test_initialize_with_twemproxy():
    """Test that using_twemproxy = True in the RedisBackend setting uses a pipeline."""
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = True
    redis_backend = RedisBackend(settings)

    redis_backend.client = mock.Mock()
    fake_pipeline = mock.Mock()
    redis_backend.client.pipeline.return_value = fake_pipeline

    redis_backend.initialize_job('my_id', {'my': 'data'}, states.PENDING, 42)

    assert fake_pipeline.execute.called == True

def test_initialize_without_twemproxy():
    """Test that using_twemproxy = False in the RedisBackend setting does not use a pipeline."""
    settings = dict(TEST_SETTINGS)
    settings['using_twemproxy'] = False
    redis_backend = RedisBackend(settings)

    redis_backend.client = mock.Mock()
    fake_pipeline = mock.Mock()
    redis_backend.client.pipeline.return_value = fake_pipeline

    redis_backend.initialize_job('my_id', {'my': 'data'}, states.PENDING, 42)

    assert fake_pipeline.execute.called == False



