#!/bin/bash

################################
# This is an ugly little hack to make
# Flock file locking work properly on the SCC
#
# Requires:
# Enigma_ExtractCortical_nipype.sh
# Enigma_ExtractSubCortical_nipype.sh
#
# ToDo:
# Move the shell scripts into datman or somewhere else
# for now I just ensure they are on the path using the job_template

SUBJECTS_DIR=$1
SUBJECT_ID=$2
OUTDIR=$3

scr_cortical=Enigma_ExtractCortical_nipype.sh
scr_subcortical=Enigma_ExtractSubCortical_nipype.sh

echo "SUBJECTS_DIR=$1" >> /tmp/argfile.$PBS_JOBID
echo "SUBJECT_ID=$2" >> /tmp/argfile.$PBS_JOBID
echo "OUTDIR=$3" >> /tmp/argfile.$PBS_JOBID

flock ~/lockfile_freesurfer -c $scr_cortical
flock ~/lockfile_freesurfer -c $scr_subcortical
rm /tmp/argfile.$PBS_JOBID
