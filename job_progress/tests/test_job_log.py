from __future__ import absolute_import

import mock
import pytest
import redis

from job_progress.job_progress import JobProgress
from job_progress.backends.redis import RedisBackend
from job_progress.tests import TEST_SETTINGS
from job_progress import utils
from job_progress import states
from job_progress import session

JobProgress.backend = RedisBackend(TEST_SETTINGS)
job_session = session.Session()
JobProgress.session = job_session


def teardown_function(function):
    # Flush the db.
    _flush_db(TEST_SETTINGS["url"])


def _flush_db(url):
    """Flush a Redis database."""
    client = redis.StrictRedis.from_url(url)
    client.flushdb()


def test_flow():
    """Verify that the whole flow works."""

    data = {"toaster": "bidule"}
    amount = 10
    job = JobProgress(data, amount)

    expected = {
        'amount': 10,
        'data': {'toaster': 'bidule'},
        'id': mock.ANY,
        'is_ready': False,
        'progress': {'PENDING': 10},
        'state': 'PENDING',
    }
    assert job.state == states.PENDING
    assert job.to_dict() == expected

    # Add all units as success
    for _ in range(amount):
        job.add_one_success()

    expected = {
        'amount': 10,
        'data': {'toaster': 'bidule'},
        'id': mock.ANY,
        'is_ready': False,
        'progress': {'SUCCESS': 10},
        'state': 'PENDING',
    }
    assert job.state == states.PENDING
    assert job.to_dict() == expected

    # Set the job itself to success
    job.state = states.SUCCESS

    expected = {
        'amount': 10,
        'data': {'toaster': 'bidule'},
        'id': mock.ANY,
        'is_ready': True,
        'progress': {'SUCCESS': 10},
        'state': 'SUCCESS',
    }
    assert job.state == states.SUCCESS
    assert job.to_dict() == expected


def test_indexes():
    """Verify that the whole flow works."""

    data = {"args": "toaster"}
    job = JobProgress(data, amount=1)

    jobs = JobProgress.query(state=states.PENDING)
    assert len(jobs) == 1
    assert jobs[0] == job

    job.state = states.SCHEDULED

    # There's no pending jobs
    jobs = JobProgress.query(state=states.PENDING)
    assert len(jobs) == 0

    # There's one scheduled job
    jobs = JobProgress.query(state=states.SCHEDULED)
    assert len(jobs) == 1
    assert jobs[0] == job

    job.state = states.STARTED

    # There's one started job
    jobs = JobProgress.query(state=states.STARTED)
    assert len(jobs) == 1
    assert jobs[0] == job

    # There's one non ready job
    jobs = JobProgress.query(is_ready=False)
    assert len(jobs) == 1
    assert jobs[0] == job

    # There's no ready jobs
    jobs = JobProgress.query(is_ready=True)
    assert len(jobs) == 0

    job.state = states.SUCCESS

    # There's one success job
    jobs = JobProgress.query(state=states.SUCCESS)
    assert len(jobs) == 1
    assert jobs[0] == job

    # There's one ready job
    jobs = JobProgress.query(is_ready=True)
    assert len(jobs) == 1
    assert jobs[0] == job

    # There's no non ready jobs
    jobs = JobProgress.query(is_ready=False)
    assert len(jobs) == 0


def test_invalid_filter():
    """Verify that we raise a TypeError on invalid filter."""

    with pytest.raises(TypeError):
        job_session.query(toaster=True)


def test_staled_job():
    """Verify that we can check if a job is staled."""
    job = JobProgress({}, amount=1)
    assert job.is_staled is False

    job.state = states.STARTED
    job.add_one_success()
    assert job.is_staled is False

    # delete the heartbeat key.
    job.backend.client.delete(job.backend._get_metadata_key(
        job.backend._get_key_for_job_id(job.id), "heartbeat"
    ))
    assert job.is_staled is True

    utils.fail_staled_jobs(JobProgress.session)
    assert job.state == states.FAILURE

    jobs = JobProgress.query(state=states.STARTED)
    assert jobs == []

    jobs = JobProgress.query(state=states.FAILURE)
    assert jobs == [job]


def test_cleanup_ready_job():
    """Verify that the cleanup job works."""
    job = JobProgress({"a": 1}, amount=1)

    utils.cleanup_ready_jobs(JobProgress.session)

    jobs = JobProgress.query()
    assert jobs == [job]

    job.state = states.FAILURE

    utils.cleanup_ready_jobs(JobProgress.session)

    jobs = JobProgress.query()
    assert jobs == []


def test_delete():
    """Verify that we can delete a job."""
    job = JobProgress({"a": 1}, amount=1)
    # To trigger indexing
    job.state = states.STARTED

    # Add a detailed progress
    job.add_one_success_detailed_progress('111')

    redis_client = redis.StrictRedis.from_url(TEST_SETTINGS["url"])

    job.delete()

    assert len(redis_client.keys("*")) == 0


def test_detailed_progress():
    """Verify that detailed progress can be successfully stored and read"""
    job = JobProgress({"a": 1}, amount=10)

    job.add_one_success_detailed_progress('111')
    assert job.get_detailed_progress(states.SUCCESS) == {
        states.SUCCESS: set(['111'])
    }
    assert job.get_detailed_progress() == {
        states.SUCCESS: set(['111'])
    }

    job.add_one_success_detailed_progress('222')
    job.add_one_failure_detailed_progress('333')
    assert job.get_detailed_progress(states.SUCCESS) == {
        states.SUCCESS: set(['111', '222'])
    }
    assert job.get_detailed_progress(states.FAILURE) == {
        states.FAILURE: set(['333'])
    }
    assert job.get_detailed_progress() == {
        states.SUCCESS: set(['111', '222']),
        states.FAILURE: set(['333'])
    }
    assert job.to_dict(True)['detailed_progress'] == {
        states.SUCCESS: set(['111', '222']),
        states.FAILURE: set(['333'])
    }
