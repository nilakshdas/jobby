from __future__ import print_function

import time
from jobby import JobbyJob


with JobbyJob(dict()) as job:
    print(time.time())
