# mypackage/jobprogress.py
from __future__ import absolute_import

from job_progress import JobProgress, Session
from job_progress.backends.redis import RedisBackend

TEST_CONFIG = {
    'backend_url': 'redis://localhost:6379/0',
}
session = Session(backend=RedisBackend(TEST_CONFIG))
JobProgress.set_session(session)
