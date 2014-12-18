from job_progress import states


def fail_staled_jobs(session):
    """Mark staled jobs as FAILURE.

    Staled definition is controlled through ``heartbeat_expiration``.
    """

    jobs = session.query(is_ready=False)
    for job in jobs:
        if job.is_staled:
            job.state = states.FAILURE


def cleanup_ready_jobs(session):
    """Cleanup jobs that are ready."""

    jobs = session.query(is_ready=True)
    for job in jobs:
        job.delete()


class classproperty(object):

    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)
