#!/bin/bash
#PBS -V
#PBS -S /bin/bash
module load Freesurfer/6.0.0
module load /external/rprshnas01/tigrlab/archive/code/datman_env_scc.module
export PYTHONPATH=$PYTHONPATH:/external/rprshnas01/tigrlab/projects/twright/Projects/pipelines/freesurfer
export PATH=$PATH:/external/rprshnas01/tigrlab/projects/twright/Projects/pipelines/freesurfer
