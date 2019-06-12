from __future__ import print_function

import os
import socket
import string
import sys
import time

from celery import Celery
from celery.signals import celeryd_after_setup
from coolname import generate_slug
import libtmux
from libtmux.exc import TmuxSessionExists

from jobby.utils import get_env


APP_NAME = 'jobby-exec'
TASK_NAME = 'run_command'
PROJECT_NAME = get_env('JOBBY_PROJECT_NAME')
NETWORK_HOST = get_env('JOBBY_NETWORK_HOST')
DATABASE_URL = '%s:27017' % NETWORK_HOST
BACKEND_URL = 'redis://%s:6379' % NETWORK_HOST
BROKER_URL = 'amqp://admin:password@%s:5672/%s' % (NETWORK_HOST, PROJECT_NAME)
RUNTIME_ENV = get_env('JOBBY_PYTHON_RUNTIME_ENV')
JOBBY_WORK_DIR = get_env('JOBBY_WORK_DIR')
JOBBY_SCRATCH_DIR = get_env('JOBBY_SCRATCH_DIR')
JOBBY_LOGS_DIR = os.path.join(JOBBY_SCRATCH_DIR, 'logs')
JOBBY_LOCKS_DIR = os.path.join(JOBBY_SCRATCH_DIR, 'locks')
CUDA_VISIBLE_DEVICES = get_env('CUDA_VISIBLE_DEVICES', required=False) or '0'


assert os.path.isdir(JOBBY_WORK_DIR)
if not os.path.exists(JOBBY_LOGS_DIR):
    os.makedirs(JOBBY_LOGS_DIR)
if not os.path.exists(JOBBY_LOCKS_DIR):
    os.makedirs(JOBBY_LOCKS_DIR)

app = Celery(APP_NAME, broker=BROKER_URL, backend=BACKEND_URL)
app.conf.update(worker_prefetch_multiplier=1, 
                worker_send_task_events=True)

new_session_id = lambda: 'jobby-%s-%s' % (
    time.strftime('%Y%m%dT%H%M%S'),
    generate_slug(2).replace('-', '_'))


@celeryd_after_setup.connect
def wait_for_networking_services(sender, instance, **kwargs):
    if 'master' in sender:
        wait = 60
        print('Waiting %ds for networking services to spin up...' % wait)
        time.sleep(wait)


@app.task(bind=True)
def run_command(self, command):
    print('Running "%s" in "%s"' % (command, JOBBY_WORK_DIR))

    hostname = socket.gethostname()
    self.update_state(
        state='STARTED',
        meta={'hostname': hostname})

    server = libtmux.Server()
    log_file, lock_file = None, None
    session, session_id = None, None
    
    while True:
        session_id = new_session_id()
        try:
            session = server.new_session(session_id)

            log_file = os.path.join(JOBBY_LOGS_DIR, '%s.log' % session_id)
            assert not os.path.exists(log_file)

            lock_file = os.path.join(JOBBY_LOCKS_DIR, '%s.lock' % session_id)
            with open(lock_file, 'w') as f:
                f.write(self.request.id)

        except (TmuxSessionExists, AssertionError):
            time.sleep(1)

        else:
            break

    assert session is not None
    assert os.path.isfile(lock_file)

    pane = session.attached_pane

    change_dir_cmd = 'cd "%s"' % JOBBY_WORK_DIR
    activate_env_cmd = 'source activate %s' % RUNTIME_ENV

    pane.send_keys(change_dir_cmd)
    if RUNTIME_ENV:
        pane.send_keys(activate_env_cmd)
        time.sleep(10)  # Waiting for env to get activated
    pane.send_keys(' '.join([
        'export CUDA_VISIBLE_DEVICES=%s;' % (CUDA_VISIBLE_DEVICES,),
        '%s |& tee "%s";' % (command, log_file),
        'rm -f "%s";' % (lock_file,),
        'exit']))

    while os.path.exists(lock_file):
        self.update_state(
            state='RUNNING',
            meta={'hostname': hostname,
                  'session_id': session_id})

        time.sleep(5)

    self.update_state(
        state='FINISHED',
        meta={'hostname': hostname,
              'session_id': session_id})

    pane.send_keys(
        'C-c', enter=False, 
        suppress_history=False)

    return hostname, session_id


if __name__ == '__main__':
    command = ' '.join(sys.argv[1:])

    result = app.send_task(
        '%s.%s' % (APP_NAME, TASK_NAME),
        args=(command,))

    start, timeout = time.time(), 30
    while True:
        now = time.time()
        if (now - start > timeout
                or result.state == 'RUNNING'):
            print(result.info)
            break
        time.sleep(1)
