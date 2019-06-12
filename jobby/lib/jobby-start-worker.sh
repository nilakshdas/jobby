#!/usr/bin/env bash

if [[ -z "${JOBBY_PROJECT_NAME}" ]]
then
    echo "✖︎ ERROR: JOBBY_PROJECT_NAME is not set"
    exit 1
fi

if [[ -z "${JOBBY_LIB_DIR}" ]]
then
    echo "✖︎ ERROR: JOBBY_LIB_DIR is not set"
    exit 1
fi

if [[ -z "${JOBBY_JOB_CONCURRENCY}" ]]
then
    echo "✖︎ ERROR: JOBBY_JOB_CONCURRENCY is not set"
    exit 1
fi

DATE_STR=$(date +%s)
RAND_STR=$(python -c "from __future__ import print_function; from coolname import generate_slug; print(generate_slug(2))")
CELERY_ID=worker.${JOBBY_PROJECT_NAME}.${DATE_STR}.${RAND_STR}@%h

cd "${JOBBY_LIB_DIR}"

celery worker -A jobby-exec \
    -l info -Ofair \
    -n ${CELERY_ID} \
    -c ${JOBBY_JOB_CONCURRENCY}
