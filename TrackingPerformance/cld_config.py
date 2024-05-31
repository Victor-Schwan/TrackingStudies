from pathlib import Path

# define environment setup script path
stable = Path("/cvmfs/sw.hsf.org/key4hep/setup.sh")
nightlies = Path("/cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh")
setup = nightlies  # choose either stable or nightlies


# ==========================
# define base directories
# ==========================

# those files are available to job
baseAFSDir = Path("/afs/cern.ch/user/") / "U/USER/CHANGE/PATH"  # FIXME
# not directly available to job, only for storing purposes
baseEOSDir = Path("/eos/") / "HOME-U/USER/CHANGE/PATH"  # FIXME

# define directory to store output
dataDir = baseEOSDir / "data"
# define dirs
SIMcondorDir = baseAFSDir / "sim" / "condor_jobs"
RECcondorDir = baseAFSDir / "rec" / "condor_jobs"
# detector specific
# FIXME: extract following from dict based on detectorModel var?
detectorDIR = baseAFSDir / "CHANGE" / "PATH"  # FIXME
sim_steering_file = detectorDIR / "CHANGE" / "PATH"  # FIXME
rec_steering_file = detectorDIR / "CHANGE" / "PATH"  # FIXME


# ==========================
# Job Parameters Initialisation
# ==========================

Nevts_ = "30"
Nevt_per_job = "10"  # Set the desired number of events per job


# ==========================
# Parameters Initialisation
# ==========================
detectorModel = ["CLD_model_1"]
detModPaths = {"CLD_model_1": Path("CHANGE/PATH")}  # FIXME
# Define lists of parameters for reconstruction
thetaList_ = ["10"]  # , "20" , "30", "40", "50", "60", "70", "80", "89"
momentumList_ = ["1", "2"]  # , "5", "10", "20", "50", "100", "200"
# momentumList_ = ["1", "10", "100"]
particleList_ = ["mu"]  # ,"e" ,"pi"]
