#!/bin/bash

PROJ_PATH="${HOME}/CODE/pyheifconcat"
SCRIPTS_PATH="${PROJ_PATH}/scripts/mila"

#REMOTE_HOME="/home/sogagne"
#REMOTE_PROJ_PATH="${REMOTE_HOME}/CODE/pyheifconcat"
#REMOTE_SCRIPTS_PATH="${REMOTE_PROJ_PATH}/scripts/beluga"

DATA_DIR="/network/data1"
HDF5_FILE="${DATA_DIR}/ilsvrc2012.hdf5"
DEST_DIR=$(readlink -f "./data")
#DEST_DIR="/home/sogagne/projects/rpp-bengioy/sogagne/pyheifconcat"
DEST_FILE="${DEST_DIR}/concat.mdat"

ITERATION_CNT=5
ITERATION_SZ=4

echo PWD=${PWD}
echo PATH=${PATH}
echo PROJ_PATH=${PROJ_PATH}
echo SCRIPTS_PATH=${SCRIPTS_PATH}
echo REMOTE_HOME=${REMOTE_HOME}
echo REMOTE_PROJ_PATH=${REMOTE_PROJ_PATH}
echo REMOTE_SCRIPTS_PATH=${REMOTE_SCRIPTS_PATH}
echo DATA_DIR=${DATA_DIR}
echo HDF5_FILE=${HDF5_FILE}
echo DEST_DIR=${DEST_DIR}
echo DEST_FILE=${DEST_FILE}
echo ITERATION_CNT=${ITERATION_CNT}
echo ITERATION_SZ=${ITERATION_SZ}
echo .

set -x

# init directories
#sbatch -c 1 --qos=low --time=0:1:0 --wait --mail-type=ALL --mail-user=satya.ortiz-gagne@mila.quebec ${SCRIPTS_PATH}/concat.sh ${DEST_DIR} ${DEST_FILE}
#ssh beluga 'export PATH=${PATH}':"${REMOTE_PROJ_PATH}/tests/mocks;" "cd ${REMOTE_PROJ_PATH};" sbatch -c 1 --qos=low --time=0:1:0 --wait --mail-type=ALL --mail-user=satya.ortiz-gagne@mila.quebec ${REMOTE_SCRIPTS_PATH}/concat.sh ${DEST_DIR} ${DEST_FILE}
sbatch -c 1 --qos=low --wait --mail-type=ALL --mail-user=satya.ortiz-gagne@mila.quebec ${SCRIPTS_PATH}/concat.sh ${DEST_DIR} ${DEST_FILE}

for (( i=0; i<${ITERATION_CNT}; i++ )); do
  START=$(( ${i} * ${ITERATION_SZ} + 1 ))
  END=$(( (${i} + 1) * ${ITERATION_SZ} ))
  sbatch -c 1 --qos=low --array=${START}-${END} --wait --mail-type=ALL --mail-user=satya.ortiz-gagne@mila.quebec ${SCRIPTS_PATH}/transcode.sh ${HDF5_FILE} ${DEST_DIR}
  sbatch -c 1 --qos=low --wait --mail-type=ALL --mail-user=satya.ortiz-gagne@mila.quebec ${SCRIPTS_PATH}/concat.sh ${DEST_DIR} ${DEST_FILE}
  #ssh beluga 'export PATH=${PATH}':"${REMOTE_PROJ_PATH}/tests/mocks;" "cd ${REMOTE_PROJ_PATH};" sbatch -c 1 --qos=low --wait --mail-type=ALL --mail-user=satya.ortiz-gagne@mila.quebec ${REMOTE_SCRIPTS_PATH}/concat.sh ${DEST_DIR} ${DEST_FILE}
done
