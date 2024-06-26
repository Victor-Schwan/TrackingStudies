#!/usr/bin/env python

import sys
from math import ceil
from os import fspath, system  # for execution at the end
from pathlib import Path

import ROOT
from utils import load_config, parse_args


def main() -> None:

    # ==========================
    # Load specified config file
    # ==========================

    args = parse_args()
    config = load_config(args.config)

    # ==========================
    # Check paths
    # ==========================

    assert (
        config.sim_steering_file.exists()
    ), f"The file {config.sim_steering_file} does not exist"
    assert (
        config.detector_dir.exists()
    ), f"The folder {config.detector_dir} does not exist"

    # ==========================
    # Parameters Initialisation
    # ==========================

    assert isinstance(config.N_EVTS, int), "config.N_EVTS must be of type integer"
    assert isinstance(
        config.N_EVTS_PER_JOB, int
    ), "config.N_EVTS_PER_JOB must be of type integer"

    n_para_sets = (
        len(config.detector_model_list)
        * len(config.particle_list)
        * len(config.theta_list)
        * len(config.momentum_list)
    )
    # number of parallel jobs with same parameter combination/set
    n_jobs_per_para_set = ceil(
        config.N_EVTS / config.N_EVTS_PER_JOB
    )  # Nevts is lower limit
    # total number of jobs, can be printed for debugging/information
    n_jobs = n_jobs_per_para_set * n_para_sets

    # ===========================
    # Directory Setup and Checks
    # ===========================

    # Define directories for input and output
    directory_jobs = (
        config.sim_condor_dir
        / f"{config.particle_list[0]}_{config.detector_model_list[0]}"
    )
    sim_eos_dir = config.data_dir / f"{config.detector_model_list[0]}" / "SIM"  # output

    # Enable output checks
    CHECK_OUTPUT = True
    """
    -does not work-
    Set to True to enable checks, False to disable
    It will check if the ouputs exist and contain correct number of events
    if not it will send job to rerun simulation
    """

    # Check if the directory exists and exit if it does
    try:
        directory_jobs.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(
            f"Error: Directory '{directory_jobs}' already exists and should not be overwritten."
        )
        sys.exit(1)

    sim_eos_dir.mkdir(
        parents=True, exist_ok=True
    )  # This will create the directory if it doesn't exist, without raising an error if it does

    # =======================
    # Simulation Job Creation
    # =======================

    # Create all possible combinations
    import itertools

    iter_of_combined_variables = itertools.product(
        config.theta_list,
        config.momentum_list,
        config.particle_list,
        config.detector_model_list,
    )

    NEED_TO_CREATE_SCRIPTS = False

    for theta, momentum, part, dect in iter_of_combined_variables:
        for task_index in range(n_jobs_per_para_set):

            output_file_name_parts = [
                f"SIM_{dect}",
                f"{part}",
                f"{theta}_deg",
                f"{momentum}_GeV",
                f"{config.N_EVTS_PER_JOB}_evts",
                f"{task_index}",
            ]

            if config.EDM4HEP_SUFFIX_WITH_UNDERSCORE:
                output_file_name_parts.append("edm4hep")
                output_file_name = Path("_".join(output_file_name_parts)).with_suffix(
                    ".root"
                )
            else:
                output_file_name = Path("_".join(output_file_name_parts)).with_suffix(
                    ".edm4hep.root"
                )

            # Check if the output file already exists and has correct Nb of events
            output_dir = sim_eos_dir / part
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file_path = output_dir / output_file_name

            # FIXME: Issue #4
            if CHECK_OUTPUT and output_file_path.exists():
                root_file = ROOT.TFile(fspath(output_file_path), "READ")
                events_tree = root_file.Get("events")
                if events_tree:
                    if events_tree.GetEntries() == config.N_EVTS_PER_JOB:
                        root_file.Close()
                        continue
                root_file.Close()
            else:
                NEED_TO_CREATE_SCRIPTS = True

            # Build ddsim command
            arguments = [
                f" --compactFile {Path('$k4geo_DIR') / config.det_mod_paths[config.detector_model_list[0]]}",
                f"--outputFile {output_file_name}",
                f"--steeringFile {config.sim_steering_file}",
                "--enableGun",
                f"--gun.particle {part}-",
                f"--gun.energy {momentum}*GeV",
                "--gun.distribution uniform",
                f"--gun.thetaMin {theta}*deg",
                f"--gun.thetaMax {theta}*deg",
                "--crossingAngleBoost 0",
                f"--numberOfEvents {config.N_EVTS_PER_JOB}",
            ]
            command = f"ddsim {' '.join(arguments)} > /dev/null"

            # Write bash script for job execution
            bash_script = (
                "#!/bin/bash \n"
                f"source {config.setup} \n"
                f"{command} \n"
                f"xrdcp {output_file_name} root://eosuser.cern.ch/{output_dir} \n"
                f"rm {output_file_name}"
            )
            bash_file_name_parts = [
                "bash_script",
                dect,
                part,
                f"{theta}_deg",
                f"{momentum}_GeV",
                str(task_index),
            ]
            bash_file_path = (
                directory_jobs / "_".join(bash_file_name_parts)
            ).with_suffix(".sh")

            with open(bash_file_path, "w", encoding="utf-8") as bash_file:
                bash_file.write(bash_script)
                bash_file.close()

    if not NEED_TO_CREATE_SCRIPTS:
        print("All output files are correct.")
        print(f"The output file path: {output_file_path}")
        sys.exit(0)

    # ============================
    # Condor Submission Script
    # ============================

    # Write the condor submission script
    condor_script = (
        "executable = $(filename) \n"
        "arguments = $(ClusterId) $(ProcId) \n"
        "output = output.$(ClusterId).$(ProcId).out \n"
        "error = error.$(ClusterId).$(ProcId).err \n"
        "log = log.$(ClusterId).log \n"
        f'+JobFlavour = "{config.JOB_FLAVOR}" \n'
        "queue filename matching files *.sh \n"
    )
    condor_file_path = directory_jobs / "condor_script.sub"
    with open(condor_file_path, "w", encoding="utf-8") as condor_file:
        condor_file.write(condor_script)
        condor_file.close()

    # ====================
    # Submit Job to Condor
    # ====================

    system(
        "cd " + fspath(directory_jobs) + "; condor_submit condor_script.sub"
    )  # FIXME: use subprocess instead?


if __name__ == "__main__":
    main()
