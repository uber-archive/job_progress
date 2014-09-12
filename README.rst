JobProgress
===========

**Store the progress of a task.**

Documentation
-------------

Latest documentation: not yet generated.

Getting Started
---------------

**Initialize JobProgress**

Before creating or loading a job instance, we must setup JobProgress's backend and session. 

.. code-block:: python

    >>> from job_progress.job_progress import JobProgress
    >>> from job_progress.backends.redis import RedisBackend
    >>> from job_progress import states, session
    >>> settings = {"url": "redis://localhost:6379/0"}
    >>> JobProgress.backend = RedisBackend(settings)
    >>> JobProgress.session = session.Session()

**Create Job**

.. code-block:: python

    >>> # 10 is the amount of work
    >>> job = JobProgress({"created_at": "2013-12-12"}, amount=10, state=states.STARTED)
    >>> # Get job id is a random uuid that we can use to get this job
    >>> job.id # doctest: +SKIP
    '02d10e4b-ee46-4a9d-bd6a-b30e710490fb'
    
**Load Job by Id**

You can load an existing job by its id.

.. code-block:: python

    >>> job = JobProgress.session.get('02d10e4b-ee46-4a9d-bd6a-b30e710490fb')
    >>> job
    <JobProgress '02d10e4b-ee46-4a9d-bd6a-b30e710490fb'>
    
**Add Success or Failure Progress**

.. code-block:: python    

    >>> # Create a new job
    >>> job = JobProgress({}, amount=10, state=states.STARTED)
    >>> job.add_one_success()
    >>> job.add_one_failure()
    >>> job.get_progress()
    {'FAILURE': 1, 'PENDING': 8, 'SUCCESS': 1}
    >>> del job
    >>> # Jobs are indexed
    >>> jobs = JobProgress.query(state=states.STARTED)
    >>> jobs[0].get_progress()
    {'FAILURE': 1, 'PENDING': 8, 'SUCCESS': 1}

**Add Detailed Progress**

.. code-block:: python

    >>> # Create a new job
    >>> job = JobProgress({}, amount=10, state=states.STARTED)
    >>> job.add_one_success("success item")
    >>> job.add_one_failure("failed item")
    >>> job.get_detailed_progress()
    {'FAILURE': set(['failed item']), 'SUCCESS': set(['success item'])}

**Use Track Helper**

.. code-block:: python

    >>> # Create a new job
    >>> job = JobProgress({}, amount=10, state=states.STARTED)
    >>> is_success = True
    >>> job.track(is_success, 'foo')
    >>> job.get_detailed_progress()
    {'SUCCESS': set(['foo'])}

Installation
------------

JobProgress is not yet on pip.

Twemproxy
---------

When using Twemproxy, moving a job between states is a non-atomic operation.

License
-------

JobProgress is available under the MIT License.

Copyright Uber 2013, Charles-Axel Dein <charles@uber.com>

Authors
-------

Charles-Axel Dein <charles@uber.com>
