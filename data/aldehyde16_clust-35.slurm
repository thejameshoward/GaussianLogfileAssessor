#!/bin/csh
#SBATCH --partition=kingspeak
#SBATCH --account=sigman
#SBATCH --time=5:00:00
#SBATCH --nodes=1
#SBATCH -o slurm-%j.out-%N
#SBATCH -e slurm-%j.err-%N
env | grep SLURM
setenv WORKDIR /uufs/chpc.utah.edu/common/home/u6053008/scripts/GaussianLogfileAssessor/data
setenv FILENAME ./aldehyde16_clust-35

# set an env variable that indicates
# whether the local or general storage
# is used
if $UUFSCELL ==  lonepeak.peaks then
   setenv SCRFLAG GENERAL
else
   setenv SCRFLAG LOCAL
endif


setenv NODES 1

# Change directories
cd /uufs/chpc.utah.edu/common/home/u6053008/scripts/GaussianLogfileAssessor/data

sed -i s/%NProcShared='.\+'/%NProcShared=$SLURM_CPUS_ON_NODE/g ${FILENAME}.com
sed -i s/%nprocshared='.\+'/%NProcShared=$SLURM_CPUS_ON_NODE/g ${FILENAME}.com
sed -i s/%nprocs='.\+'/%NProcShared=$SLURM_CPUS_ON_NODE/g ${FILENAME}.com

# Load gaussian16 depending on the system
if ($UUFSCELL ==  lonepeak.peaks | $UUFSCELL ==  ember.arches ) then
   module load gaussian16/SSE4.C01
endif
if ( $UUFSCELL ==  tangent.peaks) then
   module load gaussian16/AVX.C01
endif
if ( kingspeak.peaks ==  notchpeak.peaks) then
   module load gaussian16/AVX2.C01
   if ( $SLURM_CPUS_ON_NODE == 64 ) then
     setenv PGI_FASTMATH_CPU sandybridge
   endif
endif
if ($UUFSCELL ==  kingspeak.peaks) then
  if ($SLURM_CPUS_ON_NODE == 24 | $SLURM_CPUS_ON_NODE == 28 ) then
                module load gaussian16/AVX2.C01
  else
                module load gaussian16/AVX.C01
  endif
endif
if ($UUFSCELL ==  ash.peaks) then
  if ($SLURM_CPUS_ON_NODE == 12 ) then
                module load gaussian16/SSE4.C01
  else if ($SLURM_CPUS_ON_NODE == 20 | $SLURM_CPUS_ON_NODE == 16 ) then
                module load gaussian16/AVX.C01
  else
                module load gaussian16/AVX2.C01
  endif
endif

ml
setenv MP_NEWJOB yes
setenv LINDA_CLC network
setenv LINDA_FLC network

# Writing to scratch/local
if ($SCRFLAG == LOCAL) then
  setenv GAUSS_SCRDIR  /scratch/local/$USER/$SLURM_JOB_ID/$UUFSCELL
  mkdir -p /scratch/local/$USER/$SLURM_JOB_ID/$UUFSCELL
  mkdir -p $WORKDIR/$SLURM_JOB_ID/$UUFSCELL
   cd $WORKDIR/$SLURM_JOB_ID/$UUFSCELL
   cp $WORKDIR/$FILENAME.com .
   cp $WORKDIR/$FILENAME.chk .
endif

if ($SCRFLAG == KPSERIAL) then
  setenv GAUSS_SCRDIR  /scratch/kingspeak/serial/$USER/$SLURM_JOB_ID/$UUFSCELL
  mkdir -p /scratch/kingspeak/serial/$USER/$SLURM_JOB_ID/$UUFSCELL
   cd /scratch/kingspeak/serial/$USER/$SLURM_JOB_ID/$UUFSCELL
   cp $WORKDIR/$FILENAME.com .
   cp $WORKDIR/$FILENAME.chk .
endif
if ($SCRFLAG == GENERAL) then
  setenv GAUSS_SCRDIR  /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
  mkdir -p /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
   cd /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
   cp $WORKDIR/$FILENAME.com .
   cp $WORKDIR/$FILENAME.chk .
endif
if ($SCRFLAG == LPSERIAL) then
  setenv GAUSS_SCRDIR  /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
  mkdir -p /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
   cd /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
   cp $WORKDIR/$FILENAME.com .
   cp $WORKDIR/$FILENAME.chk .
endif
printenv
#echo $GAUSS_SCRDIR
#echo $SHELL
#echo $SLURM_NODELIST
if ($NODES == 1) then
    srun g16 $FILENAME.com
else
srun hostname -s | sort -u > tsnet.nodes.$SLURM_JOBID
cat tsnet.nodes.$SLURM_JOBID | uniq > nodes.tmp
setenv GAUSS_LFLAGS '-nodefile tsnet.nodes.$SLURM_JOBID -opt Tsnet.Node.lindarsharg: ssh'
    source /uufs/chpc.utah.edu/sys/installdir/gaussian16/etc/parascript.csh > Default.Route
    g16 $FILENAME.com
endif
if ($SCRFLAG == KPSERIAL) then
  cp *.log $WORKDIR/.
  cp *.chk $WORKDIR/.
  cp *.wfn $WORKDIR/.
  cp fort* $WORKDIR/.
  cp Test.FChk $WORKDIR/$FILENAME.FChk
  cd ..
  rm -r /scratch/kingspeak/serial/$USER/$SLURM_JOB_ID/$UUFSCELL
endif
if ($SCRFLAG == GENERAL) then
  cp *.log $WORKDIR/.
  cp *.chk $WORKDIR/.
  cp *.wfn $WORKDIR/.
  cp fort* $WORKDIR/.
  cp Test.FChk $WORKDIR/$FILENAME.FChk
  cd ..
  rm -r /scratch/general/vast/$USER/$SLURM_JOB_ID/$UUFSCELL
endif
if ($SCRFLAG == LOCAL) then
  cp *.log $WORKDIR/.
  cp *.chk $WORKDIR/.
  cp *.wfn $WORKDIR/.
  cp fort* $WORKDIR/.
  cp Test.FChk $WORKDIR/$FILENAME.FChk
  cd ..
  rm -r $WORKDIR/$SLURM_JOB_ID/$UUFSCELL
endif
cd $WORKDIR
formchk $FILENAME.chk $FILENAME.fchk
#----- End of g16job ---------
