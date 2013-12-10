"""
The following states are defined:

* .. py:data:: SUCCESS
* .. py:data:: FAILURE
* .. py:data:: REVOKED
* .. py:data:: STARTED
* .. py:data:: SCHEDULED
* .. py:data:: PENDING
* .. py:data:: READY_STATE
  (SUCCESS or FAILURE)

"""


SUCCESS = 'SUCCESS'
FAILURE = 'FAILURE'
REVOKED = 'REVOKED'
STARTED = 'STARTED'
# Kind of like Celery's RECEIVED
SCHEDULED = 'SCHEDULED'
# State is unknown
PENDING = 'PENDING'

# Task is finished
READY_STATES = frozenset([SUCCESS, FAILURE, REVOKED])
ALL_STATES = frozenset([SUCCESS, FAILURE, REVOKED,
                        SCHEDULED, STARTED, PENDING])
NOT_READY_STATES = ALL_STATES - READY_STATES
REVOKABLE_STATES = frozenset([SCHEDULED, PENDING])
