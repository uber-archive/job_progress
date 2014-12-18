Quickstart
==========

Installation
------------

Setup
-----

Subclass `JobProgressBase`:

.. literalinclude:: ../job_progress/tests/fixtures/job_progress.py


Storing progress
----------------

You can then use it from other files:

.. code-block:: python

    from job_progress import states

    from mypackage.job_progress import JobProgress


    def toast_bread(toasts):
        """Toast some bread."""
        # You can store any meta data on the job.
        job = JobProgress({'created_at': '2014-12-12'},
                          amount=len(toasts),  # Amount of work
                          state=states.STARTED)

        for toast in toasts:
            try:
                assert True  # toast bread
                job.add_one_success()
            except:
                job.add_failure()


Getting progress
----------------

If you have a specific job id, you can get the job directly:

.. code-block:: python

    from mypackage.job_progress import session

    job = session.get('31bd07a2-5174-4cbd-a575-d68382518f20')
    job.get_progress()
    # Return something like:
    # {'FAILURE': 1, 'PENDING': 8, 'SUCCESS': 1}

Jobs are also indexed:

.. code-block:: python

    from job_progress import states

    from mypackage.job_progress import session

    jobs = session.query(state=states.STARTED)


Getting started
---------------

.. code-block:: python

    >>> from job_progress.job_progress import JobProgress
    >>> from job_progress.backends.redis import RedisBackend
    >>> from job_progress import states, session
    >>> settings = {"url": "redis://localhost:6379/0"}
    >>> JobProgress.backend = RedisBackend(settings)
    >>> JobProgress.session = session.Session()
    >>> # 10 is the amount of work
    >>> job = JobProgress({"created_at": "2013-12-12"}, amount=10, state=states.STARTED)
    >>> job.add_one_success()
    >>> job.add_one_failure()
    >>> job.get_progress()
    {'FAILURE': 1, 'PENDING': 8, 'SUCCESS': 1}
    >>> del job
    >>> # Jobs are indexed
    >>> jobs = JobProgress.query(state=states.STARTED)
    >>> jobs[0].get_progress()
    {'FAILURE': 1, 'PENDING': 8, 'SUCCESS': 1}
