#!/usr/bin/env bash

if [[ -z "${JOBBY_LIB_DIR}" ]]
then
    echo "✖︎ ERROR: JOBBY_LIB_DIR is not set"
    exit 1
fi

cd "${JOBBY_LIB_DIR}"

python jobby-exec.py $@
