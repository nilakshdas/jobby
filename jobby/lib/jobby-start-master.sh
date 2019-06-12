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

if [[ -z "${JOBBY_SCRATCH_DIR}" ]]
then
    echo "✖︎ ERROR: JOBBY_SCRATCH_DIR is not set"
    exit 1
fi

if [[ -z "${JOBBY_JOB_CONCURRENCY}" ]]
then
    echo "✖︎ ERROR: JOBBY_JOB_CONCURRENCY is not set"
    exit 1
fi

DATE_STR=$(date +%s)
RAND_STR=$(python -c "from __future__ import print_function; from coolname import generate_slug; print(generate_slug(2))")
CELERY_ID=master.${JOBBY_PROJECT_NAME}.${DATE_STR}.${RAND_STR}@%h
DOCKER_ID=${JOBBY_PROJECT_NAME}_${DATE_STR}_${RAND_STR}

cd "${JOBBY_LIB_DIR}"

docker-compose --project-name ${DOCKER_ID} up --build --detach

celery worker -A jobby-exec \
    -l info -Ofair \
    -n ${CELERY_ID} \
    -c ${JOBBY_JOB_CONCURRENCY}
 
docker-compose --project-name ${DOCKER_ID} down
