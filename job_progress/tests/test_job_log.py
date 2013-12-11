from __future__ import absolute_import

import mock
import redis

from job_progress.job_progress import JobProgress
from job_progress.backends.redis import RedisBackend
from job_progress import states
from job_progress import session

SETTINGS = {
    "url": "redis://localhost:6379/0",
}
JobProgress.backend = RedisBackend(SETTINGS)
JobProgress.session = session.Session()


def teardown_function(function):
    # Flush the db.
    _flush_db(SETTINGS["url"])


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
