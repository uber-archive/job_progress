JobProgress
===========

**Store the progress of a task.**

Documentation
-------------

Latest documentation: not yet generated.

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

Installation
------------

JobProgress is not yet on pip.

Twemproxy
---------

When using Twemproxy, moving a job between states is a non-atomic operation.

License
-------

This package is available under the MIT License.

Copyright Uber 2014, Charles-Axel Dein <charles@uber.com>

Authors
-------

Charles-Axel Dein <charles@uber.com>
