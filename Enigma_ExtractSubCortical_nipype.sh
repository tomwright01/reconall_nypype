#!/bin/bash
# Extract
function create_outfile {
  echo "SubjID, LLatVent,RLatVent,Lthal,Rthal,Lcaud,Rcaud,Lput,Rput,\
    Lpal,Rpal,Lhippo,Rhippo,Lamyg,Ramyg,Laccumb,Raccumb,ICV" > ${1}
}

function usage {
  echo "Enigma_ExtractSubCortical_nipype.sh <envfile>"
  echo "This is expected to be launched using Enigma_Summaries_nipype_launcher.sh"
  echo "Options:"
  echo "<envfile> - An environment file containing SUBJECTS_DIR, SUBJECT_ID, OUTPATH"
  echo "   e.g."
  echo "   SUBJECTS_DIR=/path/to/freesurfer/dir"
  echo "   SUBJECT_ID=ID_In_Subject_dir"
  echo "   OUTPATH=/path/to/output/files/"
  echo ""
  echo "If this is launched using Enigma_ExtractCortical_nipype_launcher.sh on the SCC"
  echo "The environment file will be created automatically"
  exit 1
}

function remove_subject_from_outputs {
  sed -i /$SUBJECT_ID/d $OUTFILE
}

if [ $# -eq 0 ]; then
  ENVFILE=/tmp/argfile.$PBS_JOBID
else
  ENVFILE="$1"
fi

if [ -e $ENVFILE ]; then
  source $ENVFILE
else
  usage
fi

# Check we got the required values
if [ -z $SUBJECTS_DIR ]; then
  usage
fi
if [ -z $SUBJECT_ID ]; then
  usage
fi
if [ -z $OUTDIR ]; then
  usage
fi

OUTFILE=${OUTDIR}/LandRvolumes.csv
SUBJECT_DIR=${SUBJECTS_DIR}/${SUBJECT_ID}

if [ ! -e ${OUTFILE} ]; then
  create_outfile ${OUTFILE}
fi

remove_subject_from_outputs
printf "%s,"  "${SUBJECT_DIR}" >> ${OUTFILE}
for x in Left-Lateral-Ventricle Right-Lateral-Ventricle Left-Thalamus-Proper Right-Thalamus-Proper Left-Caudate Right-Caudate Left-Putamen Right-Putamen Left-Pallidum Right-Pallidum Left-Hippocampus Right-Hippocampus Left-Amygdala Right-Amygdala Left-Accumbens-area Right-Accumbens-area;
do

  printf "%g," `grep  ${x} ${SUBJECT_DIR}/stats/aseg.stats | awk '{print $4}'` >> ${OUTFILE}

done

printf "%g" `cat ${SUBJECT_DIR}/stats/aseg.stats | grep IntraCranialVol | awk -F, '{print $4}'` >> ${OUTFILE}
