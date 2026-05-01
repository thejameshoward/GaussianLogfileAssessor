#!/usr/bin/env python3
# coding: utf-8

'''
Analyzes Gaussian .log files
'''

from __future__ import annotations

import re
import sys
import time
import math
import shutil
import logging
import argparse
import itertools
import multiprocessing

from pathlib import Path

logger = logging.getLogger(__name__)

DESCRIPTION = '🦝 Analyzes ORCA 6 log files for common errors 🦝.'

LINK_PATTERN = re.compile(r' Entering Link\s+\d+', re.DOTALL)
INCOMPLETE_GEOM_OPT_PATTERN = re.compile(r'ERROR \!\!\!\n\s+The optimization did not converge but reached the maximum', re.DOTALL)
ZERO_DISTANCE_ERROR_PATTERN = re.compile(r'Zero distance between atoms \d+ and \d+ in Cartesian2Internal', re.DOTALL)
MULTIPLICITY_ERROR_PATTERN = re.compile(r'multiplicity \(\d+\) .+ and number of electrons \(\d+\) .+ -> impossible')

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=DESCRIPTION,
                                     formatter_class=lambda prog: argparse.RawTextHelpFormatter(prog, 2, 40),
                                     usage=argparse.SUPPRESS)

    parser.add_argument('-i', '--input',
                        dest='input',
                        help='Directory or file to analyze. (default=cwd)\n\n',
                        metavar='')

    parser.add_argument('--dry',
                        action='store_true',
                        help='Disables creation of directories and file movement\n\n')

    parser.add_argument('-p', '--parallel',
                        action='store_true',
                        help='Uses multiprocessing to analyze files\n\n')

    parser.add_argument('--deletegbw',
                        action='store_true',
                        help='Deletes all .gbw files that have a corresponding completed .out file\n\n')

    parser.add_argument('-t', '--tolerance',
                        dest='tolerance',
                        required=False,
                        type=float,
                        default='1e-5',
                        help='Sets the tolerance value for determining oscillating optimizations (default=1e-5).\n\n',
                        metavar='')

    parser.add_argument('-w', '--window',
                        dest='window',
                        required=False,
                        type=int,
                        default=10,
                        help='Number of optimization steps to look at when evaluating oscillations (default=10).\n\n',
                        metavar='')

    parser.add_argument('--no-oscillation-criteria',
                        action='store_false',
                        help='Disables detection of oscillations to increase assessment speed.\nOscillations appear as ambiguous failed jobs\n\n')

    parser.add_argument('--debug',
                        action='store_true',
                        help='Print debug information\n\n')

    args = parser.parse_args()

    return args

def set_single_proc_affinity():
    '''
    Restricts the CPU affinity of the current process to a single core.

    Limits script execution to the first available core, ensuring
    that the script runs on a single processor. If the `psutil` module is
    not installed, or if the platform does not support CPU affinity,
    a warning is printed and no restriction is applied.

    Parameters
    ----------
    None

    Returns
    -------
    None
    '''
    try:
        import psutil
        proc = psutil.Process()
        proc.cpu_affinity([proc.cpu_affinity()[0]])
    except ModuleNotFoundError:
        logger.warning('psutil module was not found. Running on multiple cores!')
    except AttributeError:
        logger.warning('CPU affinity is not supported on this platform (e.g. macOS). Running on multiple cores!')


def get_file_text(file: Path) -> str:
    '''
    Reads the entire contents of a text file and returns it as a string.

    Parameters
    ----------
    file : Path
        Path to the file to be read.

    Returns
    ----------
    str
        The raw text content of the file.

    Raises
    ----------
    FileNotFoundError
        If the specified file does not exist.

    UnicodeDecodeError
        If the file cannot be decoded using UTF-8.
    '''
    with open(file, 'r', encoding='utf-8') as infile:
        return infile.read()


def get_orca_out_files(parent_dir: Path) -> list[Path]:
    '''
    Given a directory (parent_dir), gets all the ORCA6 .out files
    from that directory and returns a list of Path objects for the
    files.
    '''
    # Check if its a single file
    if not parent_dir.is_dir():
        if not parent_dir.suffix == '.out':
            raise TypeError('Input must be a directory of ORCA6 .out files or a single .out file.')
        files = [parent_dir]    # Convert to list for later logic
    else:
        files = [x for x in parent_dir.glob('*.out')] # Get all the log files

    if len(files) == 0:
        raise FileNotFoundError(f'No log files found in {parent_dir.absolute()}')

    return files

def get_slurm_error_file(file: Path) -> Path | None:
    '''
    Identifies the SLURM error file corresponding to a given job file
    by matching the file stem in the filename.

    Parameters
    ----------
    file : Path
        Path to the Gaussian16 .log file.

    Returns
    -------
    Path or None
        The matched SLURM error file if exactly one match is found;
        otherwise, None.
    '''

    files = [x for x in file.parent.glob(f'{file.stem}*.*error')]

    if len(files) != 1:
        return None

    return files[0]

def check_slurm_failure(slurm_error_file: Path) -> str | None:
    '''
    Checks whether a SLURM job was preempted based on the last line
    of the associated SLURM error file.

    Parameters
    ----------
    slurm_error_file : Path
        Path to the SLURM error file.

    Returns
    -------
    bool
        True if the last line contains 'PREEMPTION'; False otherwise.
    '''
    with open(slurm_error_file, 'r', encoding='utf-8') as infile:
        text = infile.read()

    if 'PREEMPTION' in text:
        return 'preempted'
    elif 'oom_kill' in text:
        return 'oom_kill'
    elif 'DUE TO TIME LIMIT' in text:
        return 'wall time exceeded'
    elif 'CANCELLED' in text:
        return 'cancelled'
    else:
        return None


def _is_logfile_complete(split_text: list[str]) -> bool:
    if split_text == ['']:
        return False

    if '****ORCA TERMINATED NORMALLY****' in split_text[-2] or '****ORCA TERMINATED NORMALLY****' in split_text[-3]:
        return True

    return False


def evaluate_orca_out_file(file: Path,
                           window: int,
                           tolerance: float,
                           check_oscillation: bool = True) -> tuple[bool, list]:
    '''
    Evaluates an ORCA6 out file to determine whether it completed successfully,
    encountered an error, or terminated abnormally.

    Parameters
    ----------
    file : Path
        Path to the ORCA6 .out file to be analyzed.

    Returns
    ----------
    tuple[Path, None, str]
        If the .out completed successfully, returns the file path and its text.

    tuple[Path, str, str]
        If the .out encountered an error, returns the file path, an error message,
        and the file text.

    tuple[Path, None, None]
        If the .out is incomplete or running, returns the file path and None values.
    '''
    # Make a list for the reason(s) the logfile failed
    failure_reasons = []

    try:
        text = get_file_text(file)
    except UnicodeDecodeError:
        return file, 'UNICODE DECODE ERROR. CHECK FILE MANUALLY', None

    split_text = text.split('\n')

    # Get the slurm error file (if it exists)
    slurm_error_file = get_slurm_error_file(file=file)

    # Check for SLURM level errors
    if slurm_error_file is not None:
        _slurm_failure_reason = check_slurm_failure(slurm_error_file)
        if _slurm_failure_reason is not None:
            failure_reasons.append(_slurm_failure_reason)

    # Check for libxc error
    if 'Error: Invalid or unknown value for Exchange in DFT XC-Kernel. Please try using LIBXC instead!' in text:
        failure_reasons.append('Invalid/unknown value for Exchange in DFT XC-Kernel. Use LIBXC(<functional>)')

    # Check for failed geometry optimization error
    if len(re.findall(INCOMPLETE_GEOM_OPT_PATTERN, text)) != 0:
        failure_reasons.append('incomplete geometry optimization')

    zero_distance_errors = re.findall(ZERO_DISTANCE_ERROR_PATTERN, text)
    if zero_distance_errors:
        failure_reasons.append(zero_distance_errors[0])

    multiplicity_errors = re.findall(MULTIPLICITY_ERROR_PATTERN, text)
    if multiplicity_errors:
        failure_reasons.append(multiplicity_errors[0])

    # Check for this warning
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !   SERIOUS PROBLEM WITH INTERNALS - ANGLE IS APPROACHING 180 OR 0 DEGREES   !
    # !                       REBUILDING A NEW SET OF INTERNALS                    !
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    if not _is_logfile_complete(split_text=split_text):
        if len(failure_reasons) == 0:
            failure_reasons.append('is incomplete (generic failure)')

    if len(failure_reasons) == 0:
        return True, failure_reasons

    return False, failure_reasons

def _collect_files_to_move(file: Path) -> list[Path]:
    '''
    Collects all files associated with a given ORCA log file.

    Parameters
    ----------
    file: Path
        Path to the ORCA .log file

    Returns
    -------
    files: list[Path]
        List of all associated files that exist on disk
    '''
    _input_file = file.with_suffix('.inp')
    if not _input_file.exists():
        _input_file = file.with_suffix('.orcainp')

    exact_files = [
        file,
        _input_file,
        _input_file.parent / f'{_input_file.stem}.slurm',
    ]

    glob_patterns = [
        f'{_input_file.stem}*.output',
        f'{_input_file.stem}*.error',
        f'{_input_file.stem}*.bibtex',
        f'{_input_file.stem}*.densitiesinfo',
        f'{_input_file.stem}*.xyz',
        f'{_input_file.stem}*.gbw',
        f'{_input_file.stem}*.densities',
        f'{_input_file.stem}*.hess',
    ]

    globbed_files = [
        match
        for pattern in glob_patterns
        for match in _input_file.parent.glob(pattern)
    ]

    return [f for f in exact_files + globbed_files if f.exists()]


def _move_file_group(files: list[Path],
                     parent_dir: Path,
                     dest_dir: Path,
                     color: str,
                     log_fn,
                     dry: bool) -> None:
    '''
    Logs and optionally moves a list of files to a destination directory.

    Parameters
    ----------
    files: list[Path]
        List of files to move

    parent_dir: Path
        Source directory from which files are moved

    dest_dir: Path
        Destination directory to move files into

    color: str
        Terminal color code to apply to logged filenames

    log_fn: callable
        Logger method to use (e.g. logger.info or logger.error)

    dry: bool
        If True, log actions without moving files

    Returns
    -------
    None
    '''
    for file in files:
        log_fn('%s%s%s', color, file.name, bcolors.ENDC)
        if not dry:
            shutil.move(parent_dir / file.name, dest_dir / file.name)


def print_analysis_and_move_files(failed: dict,
                                  completed: list[Path],
                                  files: list[Path],
                                  parent_dir: Path,
                                  delete_gbw: bool = False,
                                  dry: bool = False) -> None:
    '''
    Prints a colorful analysis of the processed ORCA log files and
    moves them into completed or failed subdirectories.

    Parameters
    ----------
    failed: dict
        Dictionary of Path:reason pairs where reason is a string
        containing an explanation of what went wrong.

    completed: list[Path]
        List of completed ORCA .log files as pathlib.Path objects

    files: list[Path]
        List of all ORCA .log files

    parent_dir: Path
        Directory on which the script operated

    delete_gbw: bool
        Whether to delete .gbw files instead of moving them

    dry: bool
        If True, log actions without moving or creating directories

    Returns
    -------
    None
    '''
    if not dry:
        for subdir in ('completed', 'failed'):
            target = parent_dir / subdir
            if not target.exists():
                target.mkdir()

    completed_dir = parent_dir / 'completed'
    failed_dir = parent_dir / 'failed'

    logger.info('-----------------------FILES MOVED TO COMPLETED DIRECTORY-----------------------')
    for file in completed:
        associated = _collect_files_to_move(file)
        _move_file_group(associated, parent_dir, completed_dir, bcolors.OKGREEN, logger.info, dry)

    logger.info('-------------------------FILES MOVED TO FAILED DIRECTORY------------------------')
    for file in failed.keys():
        associated = _collect_files_to_move(file)
        _move_file_group(associated, parent_dir, failed_dir, bcolors.FAIL, logger.error, dry)

    logger.info('TOTAL    :    %d', len(files))
    logger.info('COMPLETED:    %d (%d of %d)', len(completed), len(completed), len(files))
    logger.info('FAILED   :    %d (%d of %d)', len(failed), len(failed), len(files))


def print_summary(failed: dict,
                  completed: list[Path],
                  files: list[Path]):
    '''
    Prints a colorful analysis of only the failed files including
    a reason. Also prints a summary of all files (total number completed
    or failed).

    Parameters
    ----------
    failed: dict
        Dictionary of Path:reason pairs where reason is a string
        containing an explanation of what went wrong.

    completed: list[Path]
        List of completed G16 .log files as pathlib.Path objects

    files: list[Path]
        List of all G16 .log files

    Returns
    -------
    None
    '''
    logger.info('------------------------------------OVERVIEW------------------------------------')
    if len(failed) != 0:
        # Pad filenames to the longest name in the failed dict
        max_len = max(len(file.name) for file in failed)
        for file, reason in failed.items():
            padded = file.name.ljust(max_len)
            logger.error('%s%s%s failed because %s', bcolors.FAIL, padded, bcolors.ENDC, reason)

    logger.info('TOTAL    :    %d', len(files))
    logger.info('COMPLETED:    %d (%d of %d)', len(completed), len(completed), len(files))
    logger.info('FAILED   :    %d (%d of %d)', len(failed), len(failed), len(files))

def main() -> None:
    '''
    Main function for running the script.
    '''
    args = get_args()

    logging.basicConfig(
        level=logging.DEBUG,
        format='[%(levelname)-5s - %(asctime)s] [%(module)s] %(message)s',
        datefmt='%m/%d/%Y:%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Note the time
    t1 = time.time()

    # Input parsing
    if args.input is None:
        parent_dir = Path().cwd()
    else:
        parent_dir = Path(args.input)

    if not args.parallel:
        set_single_proc_affinity()

    # Get the logfiles
    files = get_orca_out_files(parent_dir)

    # Sort into failed dicts with files as keys and reasons as values.
    # Completed is just a list of Paths
    failed = {}
    completed = []
    logger.info('Analyzing %d files...', len(files))

    if len(files) >= 200:
        logger.info('This may take a minute.')

    # Iterate through the files
    if args.parallel:
        with multiprocessing.Pool() as p:
            results = p.starmap(evaluate_orca_out_file, zip(files,
                                                          itertools.repeat(args.window),
                                                          itertools.repeat(args.tolerance),
                                                          itertools.repeat(False),
                                                          itertools.repeat(args.no_oscillation_criteria)))

            completed = [files[i] for i, x in enumerate(results) if x[0]]
            failed = {files[i]: '\t'.join(x[1]) for i, x in enumerate(results) if x[0] is False}
    else:
        for file in files:

            if args.debug:
                logger.debug('Working on file %s', file.name)

            is_complete, reasons = evaluate_orca_out_file(file,
                                                          window=args.window,
                                                          tolerance=args.tolerance,
                                                          check_oscillation=args.no_oscillation_criteria)



            if is_complete and file not in failed.keys():
                completed.append(file)
            else:
                failed[file] = '\t'.join(reasons)

    print_summary(failed,
                  completed=completed,
                  files=files)

    # Print out the overall analysis
    if not args.dry:
        print_analysis_and_move_files(failed,
                                      completed=completed,
                                      files=files,
                                      parent_dir=parent_dir,
                                      delete_gbw=bool(args.deletegbw),
                                      dry=bool(args.dry))

    logger.info('Total analysis time (s): %.2f', round(time.time() - t1,2))

if __name__ == "__main__":
    main()