#!/usr/bin/env python3
# coding: utf-8

'''
Analyzes Gaussian .log files
'''

from __future__ import annotations

import re
import time
import math
import shutil
import logging
import argparse
import multiprocessing

from pathlib import Path

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
                        help='Directory/file to analyze. (default=cwd)\n\n')

    parser.add_argument('--debug',
                        action='store_true',
                        help='Debug information\n\n')

    parser.add_argument('--line-by-line',
                        action='store_true',
                        help='Requests printing of line-by-line analysis of each file\n\n')

    parser.add_argument('--dry',
                        action='store_true',
                        help='Disables creation of directories and file movement\n\n')

    parser.add_argument('-p', '--parallel',
                        action='store_true',
                        help='Uses multiprocessing to rapidly analyze files.\n\n')

    parser.add_argument('--deletechk',
                        action='store_true',
                        help='Deletes ALL large .chk files that have a corresponding log instead of moving them.\n\n')

    parser.add_argument('-t', '--tolerance',
                        dest='tolerance',
                        required=False,
                        default='1e-3',
                        help='Sets the tolerance value for determining oscillating optimizations.\n\n')

    args = parser.parse_args()

    if args.parallel and args.line_by_line:
        raise NotImplementedError('Cannot perform line-by-line analysis in parallel.')

    if args.deletechk:
        raise ValueError('--deletechk is not available for ORCA6LogAssesor')

    return args

def set_single_proc_affinity():
    '''
    Restricts the CPU affinity of the current process to a single core.

    Limits script execution to the first available core, ensuring
    that the script runs on a single processor. If the `psutil` module is
    not installed, a warning is printed, and no restriction is applied.

    Parameters
    ----------
    None

    Returns
    ----------
    None
    '''
    try:
        import psutil
        proc = psutil.Process()
        proc.cpu_affinity([proc.cpu_affinity()[0]])
    except ModuleNotFoundError:
        print(f'[WARNING] psutil module was not found. Running on multiple cores!')
        pass

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

def get_job_start_line_numbers(text: str) -> list[int]:
    '''
    Identifies line numbers in a Gaussian log file where a new
    computational job or link step begins.

    Parameters
    ----------
    text : str
        The complete text of the Gaussian log file.

    Returns
    ----------
    list[int]
        A list of line numbers where new job steps or internal links
        are initiated. Each of these lines should be followed by a
        "Normal termination" line in a successfully completed calculation.
    '''
    lines = text.split('\n')

    # Lines after which a normal termination should appear
    termination_indicator_lines = []

    # Geometry Optimization Run
    # THE OPTIMIZATION HAS CONVERGED
    # ****ORCA TERMINATED NORMALLY****

    for i, line in enumerate(lines):
        if re.match(LINK_PATTERN, line) is not None:
            termination_indicator_lines.append(i)
        elif re.match(PROCEDING_JOB_STEP_PATTERN, line) is not None:
            termination_indicator_lines.append(i)

    return termination_indicator_lines

def get_job_error_line_numbers(text: str) -> list[int]:
    '''
    Gets the line numbers that indicate an error has
    occured.
    '''
    lines = text.split('\n')

    error_lines = []

    for i, line in enumerate(lines):

        if re.match(FILEIO_ERROR_NON_EXISTENT_FILE, line) is not None:
            error_lines.append(i)

        elif re.match(ERRORNEOUS_WRITE, line) is not None:
            error_lines.append(i)

        elif re.match(N_STEPS_EXCEEDED, line) is not None:
            error_lines.append(i)

    return error_lines

def get_termination_line_numbers(text: str) -> list[int]:
    '''
    Gets the line numbers that indicate a new link
    or an internal job. Successful calculations should
    have a "Normal termination" line after each of these.
    '''
    lines = text.split('\n')

    # Lines after which a normal termination should appear
    terms = []
    for i, line in enumerate(lines):
        if ' Normal termination of Gaussian 16' in line:
            terms.append(i)
    return terms

def _is_logfile_complete(split_text: list[str]) -> bool:
    if split_text == ['']:
        return False

    if '****ORCA TERMINATED NORMALLY****' in split_text[-2] or '****ORCA TERMINATED NORMALLY****' in split_text[-3]:
        return True

    return False

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

def evaluate_orca_out_file(file: Path) -> tuple[Path, None, str] | tuple[Path, str, str] | tuple[Path, None, None]:
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
    try:
        text = get_file_text(file)
    except UnicodeDecodeError:
        return file, 'UNICODE DECODE ERROR. CHECK FILE MANUALLY', None

    split_text = text.split('\n')

    # Check for libxc error
    if 'Error: Invalid or unknown value for Exchange in DFT XC-Kernel. Please try using LIBXC instead!' in text:
        return file, 'Invalid/unknown value for Exchange in DFT XC-Kernel. Use LIBXC(<functional>)', text

    # Check for failed geometry optimization error
    if len(re.findall(INCOMPLETE_GEOM_OPT_PATTERN, text)) != 0:
        return file, 'incomplete geometry optimization', text

    zero_distance_errors = re.findall(ZERO_DISTANCE_ERROR_PATTERN, text)
    if zero_distance_errors:
        return file, str(zero_distance_errors[0]), text

    multiplicity_errors = re.findall(MULTIPLICITY_ERROR_PATTERN, text)
    if multiplicity_errors:
        return file, str(multiplicity_errors[0]), text


    # Check for this warning
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !   SERIOUS PROBLEM WITH INTERNALS - ANGLE IS APPROACHING 180 OR 0 DEGREES   !
    # !                       REBUILDING A NEW SET OF INTERNALS                    !
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    if not _is_logfile_complete(split_text=split_text):
        return file, 'is incomplete', text

    return file, None, text

def print_analysis_and_move_files(failed: dict,
                                  completed: list[Path],
                                  files: list[Path],
                                  parent_dir: Path,
                                  delete_chk: bool = False) -> None:
    '''
    Prints a colorful analysis of the processed G16 log files.

    Parameters
    ----------
    failed: dict
        Dictionary of Path:reason pairs where reason is a string
        containing an explanation of what went wrong.

    completed: list[Path]
        List of completed G16 .log files as pathlib.Path objects

    files: list[Path]
        List of all G16 .log files

    parent_dir: Path
        Directory on which the script operated

    delete_chk: bool
        Whether to delete .chk files instead of moving them

    Returns
    ----------
    None
    '''
    if not args.dry:
        # Make the new folders
        completed_dir = parent_dir / 'completed'
        if not completed_dir.exists():
            completed_dir.mkdir()
        failed_dir = parent_dir / 'failed'
        if not failed_dir.exists():
            failed_dir.mkdir()

    print('-----------------------FILES MOVED TO COMPLETED DIRECTORY-----------------------')
    for file in completed:

        # Define the input file that made the calculation
        _input_file = file.with_suffix('.inp')
        if not _input_file.exists():
            _input_file = file.with_suffix('.orcainp')

        # Define the additional files that we should move
        files_to_move = [
            file,
            _input_file,
            # Those with .orcainp.extension
            Path(_input_file.parent / f'{_input_file.name}.bibtex'),
            Path(_input_file.parent / f'{_input_file.name}.densitiesinfo'),
            Path(_input_file.parent / f'{_input_file.name}.xyz'),
            Path(_input_file.parent / f'{_input_file.name}.gbw'),
            Path(_input_file.parent / f'{_input_file.name}.densities'),
            Path(_input_file.parent / f'{_input_file.name}.hess'),

            Path(_input_file.parent / f'{_input_file.stem}.slurm'),

            # Those with stem.extension
            Path(_input_file.parent / f'{_input_file.stem}.bibtex'),
            Path(_input_file.parent / f'{_input_file.stem}.densitiesinfo'),
            Path(_input_file.parent / f'{_input_file.stem}.xyz'),
            Path(_input_file.parent / f'{_input_file.stem}.gbw'),
            Path(_input_file.parent / f'{_input_file.stem}.densities'),
            Path(_input_file.parent / f'{_input_file.stem}.hess'),
        ]

        # Move the files
        for _ in files_to_move:
            if _.exists():
                print(f'{bcolors.OKGREEN}{_.name}{bcolors.ENDC}')
                if not args.dry:
                    shutil.move(parent_dir / _.name, completed_dir / _.name)

    print('-------------------------FILES MOVED TO FAILED DIRECTORY------------------------')
    for file in failed.keys():

        # Define the input file that made the calculation
        _input_file = file.with_suffix('.inp')
        if not _input_file.exists():
            _input_file = file.with_suffix('.orcainp')

        # Define the additional files that we should move
        files_to_move = [
            file,
            _input_file,
            # Those with .orcainp.extension
            Path(_input_file.parent / f'{_input_file.name}.bibtex'),
            Path(_input_file.parent / f'{_input_file.name}.densitiesinfo'),
            Path(_input_file.parent / f'{_input_file.name}.xyz'),
            Path(_input_file.parent / f'{_input_file.name}.gbw'),
            Path(_input_file.parent / f'{_input_file.name}.densities'),
            Path(_input_file.parent / f'{_input_file.name}.hess'),

            Path(_input_file.parent / f'{_input_file.stem}.slurm'),

            # Those with stem.extension
            Path(_input_file.parent / f'{_input_file.stem}.bibtex'),
            Path(_input_file.parent / f'{_input_file.stem}.densitiesinfo'),
            Path(_input_file.parent / f'{_input_file.stem}.xyz'),
            Path(_input_file.parent / f'{_input_file.stem}.gbw'),
            Path(_input_file.parent / f'{_input_file.stem}.densities'),
            Path(_input_file.parent / f'{_input_file.stem}.hess'),
        ]

        # Move the files
        for _ in files_to_move:
            if _.exists():
                print(f'{bcolors.FAIL}{_.name}{bcolors.ENDC}')
                if not args.dry:
                    shutil.move(parent_dir / _.name, failed_dir / _.name)

    print('\n')
    print(f'{bcolors.BOLD}TOTAL{bcolors.ENDC}:\t\t{len(files)}')
    print(f'{bcolors.BOLD}COMPLETED{bcolors.ENDC}:\t{len(completed)} ({len(completed)} of {len(files)})')
    print(f'{bcolors.BOLD}FAILED{bcolors.ENDC}:\t\t{len(failed)} ({len(failed)} of {len(files)})')
    print('\n')

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
    ----------
    None
    '''
    print('------------------------------------OVERVIEW------------------------------------')
    if len(failed) != 0:
        for file, reason in failed.items():
            print(f'{bcolors.FAIL}{file.name}{bcolors.ENDC} failed because {reason}')

    print('\n')
    print(f'{bcolors.BOLD}TOTAL{bcolors.ENDC}:\t\t{len(files)}')
    print(f'{bcolors.BOLD}COMPLETED{bcolors.ENDC}:\t{len(completed)} ({len(completed)} of {len(files)})')
    print(f'{bcolors.BOLD}FAILED{bcolors.ENDC}:\t\t{len(failed)} ({len(failed)} of {len(files)})')
    print('\n')

def main(args) -> None:
    '''
    Main function for running the script.
    '''
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
    print(f'Analyzing {len(files)} files...')

    if len(files) >= 200:
        print('This may take a minute.')

    # Iterate through the files
    if args.parallel:
        with multiprocessing.Pool() as p:
            results = p.map(evaluate_orca_out_file, files)
            completed = [x[0] for x in results if x[1] is None]
            failed = {x[0]: x[1] for x in results if x[1] is not None}
    else:
        for file in files:

            file, logfile_assessment, file_text = evaluate_orca_out_file(file)

            if args.line_by_line:
                if file_text is None:
                    print(f'Could not perform line-by-line analysis because {logfile_assessment}')
                else:
                    #print_line_by_line_analysis(file, file_text)
                    print('LINE BY LINE ANALYSIS IS NOT AVAILABLE')

            if logfile_assessment is None and file not in failed.keys():
                completed.append(file)
            else:
                failed[file] = logfile_assessment

    # Print out the overall analysis
    if not args.dry:
        print_analysis_and_move_files(failed,
                                      completed=completed,
                                      files=files,
                                      parent_dir=parent_dir,
                                      delete_chk=bool(args.deletechk))

    print_summary(failed,
                  completed=completed,
                  files=files)

    print(f'Total analysis time (s): {round(time.time() - t1,2)}')

if __name__ == "__main__":
    args = get_args()

    if args.deletechk:
        print(f'{bcolors.FAIL}\n\nWARNING\tWARNING\tWARNING\tWARNING\n{bcolors.ENDC}')
        print(f'{bcolors.WARNING}You have selected to delete .chk files. This action is permanent.{bcolors.ENDC}')
        print(f'{bcolors.WARNING}This feature is experimental and has not been fully tested.{bcolors.ENDC}')
        print(f'{bcolors.WARNING}Copy your data to a safe location before proceeding.{bcolors.ENDC}')
        print(f'{bcolors.FAIL}\n\nWARNING\tWARNING\tWARNING\tWARNING\t{bcolors.ENDC}')
        response = input('Proceed (YES/no)?: ')

        if response.casefold() not in ['y', 'yes']:
            print(f'Response was {response.casefold}. Exiting gracefully.')
            exit()

    main(args)