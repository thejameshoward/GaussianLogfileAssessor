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
import argparse
import multiprocessing

from pathlib import Path


DESCRIPTION = '🦝 Analyzes Gaussian 16 log files for common errors 🦝.'

LINK_PATTERN = re.compile(r' Entering Link\s+\d+', re.DOTALL)
NORM_TERM_PATTERN = re.compile(r' Normal termination of Gaussian 16', re.DOTALL)
PROCEDING_JOB_STEP_PATTERN = re.compile(r'\s+Link1:\s+Proceeding to internal job step number\s+', re.DOTALL)
FILEIO_ERROR_NON_EXISTENT_FILE = re.compile(r'\s+FileIO operation on non-existent file', re.DOTALL)
ERRORNEOUS_WRITE = re.compile(r'Erroneous write. Write\s+(-|)\d+\s+instead of \d+.',  re.DOTALL)
FREQ_START_PATTERN = re.compile(r'(?<=\n Frequencies --)(.*?)(?=\n Red. masses --)', re.DOTALL)
N_STEPS_EXCEEDED = re.compile(r'\s+--\s+Number of steps exceeded,\s+NStep= \d+')

MAX_FORCE_PATTERN = re.compile(r'Maximum Force\s+\d+\.\d+\s+\d+\.\d+\s+(?:NO|YES)')
RMS_FORCE_PATTERN = re.compile(r'RMS     Force\s+\d+\.\d+\s+\d+\.\d+\s+(?:NO|YES)')
MAX_DISPLACEMENT_PATTERN = re.compile(r'Maximum Displacement\s+\d+\.\d+\s+\d+\.\d+\s+(?:NO|YES)')
RMS_DISPLACEMENT_PATTERN = re.compile(r'RMS     Displacement\s+\d+\.\d+\s+\d+\.\d+\s+(?:NO|YES)')

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

    args = parser.parse_args()

    if args.parallel and args.line_by_line:
        raise NotImplementedError(f'Cannot perform line-by-line analysis in parallel.')

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

def get_n_normal_terminations(text: str) -> int:
    return len(re.findall(NORM_TERM_PATTERN, text))

def get_n_links(text: str) -> int:
    return len(re.findall(LINK_PATTERN, text))

def has_imaginary_frequency(text: str) -> tuple[bool, float]:
    '''
    Determines if log file has imaginary frequencies
    '''
    return float(re.split(r'\s+', re.search(FREQ_START_PATTERN, text).group().strip())[0]) <= 0, float(re.split(r'\s+', re.search(FREQ_START_PATTERN, text).group().strip())[0])

def has_frequency_section(text: str) -> bool:
    '''
    Determines if log file has a frequency section
    '''
    return re.search(FREQ_START_PATTERN, text) is not None

def print_line_by_line_analysis(file: Path, text: str):

    # For printing headers
    len_file_name = len(file.name)
    spacer = (80 - len_file_name) / 2
    print('-'* math.ceil(spacer) + file.name + '-'* math.floor(spacer))

    # Print the debug information
    lines = text.split('\n')

    print(f'\tNumber of link statements\t\t{get_n_links(text)}')
    print(f'\tNumber of termination statements:\t{get_n_normal_terminations(text)}\n')

    print('\tLine-by-line analysis:')
    for i, line in enumerate(lines):
        if re.match(LINK_PATTERN, line) is not None:
            print(f'\t\tENTER LINK\t\t\t{i+1}')

        elif re.match(PROCEDING_JOB_STEP_PATTERN, line) is not None:
            print(f'\t\tINTERNAL JOB\t\t\t{i+1}')

        elif ' Normal termination of Gaussian 16' in line:
            print(f'\t\tNORM TERM\t\t\t{i+1}')

        elif 'FileIO operation on non-existent file' in line:
            print(f'\t\tFileIO Error (non-existent)\t{i+1}')

        elif 'Erroneous write.' in line:
            print(f'\t\tERRONEOUS WRITE\t\t\t{i+1}')

        else:
            pass

    print('\n')

def _is_logfile_complete(split_text: list[str]) -> bool:
    if split_text == ['']:
        return False

    if 'Normal termination of Gaussian 16' in split_text[-1] or 'Normal termination of Gaussian 16' in split_text[-2]:
        return True

    return False

def get_slurm_out_file(file: Path) -> Path | None:
    files = [x for x in file.parent.glob('*out*') if file.stem in x.name]

    if files == []:
        return None

    # Check if only one output file exists
    if len(files) != 1:
        print(f'{bcolors.FAIL}WARNING: Multiple SLURM output files identified for {file.name}.{bcolors.ENDC}')

    return files[0]

def get_slurm_error_file(file: Path) -> Path | None:
    '''
    Finds an error file that contains the file stem.
    Returns None if exactly 1 file was not found.
    '''
    files = [x for x in file.parent.glob('*error*') if file.stem in x.name]

    # Return None if there is not exactly 1 file
    if len(files) != 1:
        return None

    return files[0]

def job_preempted(file: Path) -> bool:
    slurm_out = get_slurm_error_file(file)

    if slurm_out is None:
        return False

    with open(slurm_out, 'r') as infile:
        lines = infile.readlines()

    if 'PREEMPTION' in lines[-1]:
        return True
    return False

def job_cancelled(file: Path) -> bool:
    slurm_out = get_slurm_error_file(file)

    if slurm_out is None:
        return False

    with open(slurm_out, 'r') as infile:
        lines = infile.readlines()

    if 'CANCELLED' in lines[-1]:
        return True
    return False

def get_slurm_job_id_from_log_file(text: str) -> int:

    SCRDIR_PATTERN = re.compile(r'(?<=scrdir=\")(.*?)(?=\")', re.DOTALL)
    match = re.search(SCRDIR_PATTERN, text)

    if match is None:
        print(f'Could not find slurm job ID!')
        return None

    match = Path(match[0].strip())

    # Assume the job_id is in the last part of the path
    match = match.parts[-1]

    try:
        match = int(''.join([x for x in str(match) if x.isdigit()]))
    except ValueError as e:
        pass

def _is_oscillating(values: list[float], window=3) -> float:
    oscillating_values = set()
    for i, value in enumerate(values):
        if i < 2:
            continue
    raise NotImplementedError
    return list(oscillating_values)[0]

def check_oscillating_optimization_criteria(text: str) -> tuple[bool, str]:
    '''
    Tests whether an optimization is oscillating
    '''
    from pprint import pprint
    for pattern in [MAX_DISPLACEMENT_PATTERN, RMS_DISPLACEMENT_PATTERN, MAX_FORCE_PATTERN, RMS_FORCE_PATTERN]:
        matches = re.findall(pattern, text)
        if len(matches) == 0:
            continue
        matches = [float(x.split()[1]) for x in matches]

    exit()

def get_logfiles(parent_dir: Path) -> list[Path]:
    '''
    Given a directory (parent_dir), gets all the Gaussian16 logfiles
    from that directory and returns a list of Path objects for the
    files.
    '''
    # Check if its a single file
    if not parent_dir.is_dir():
        if not parent_dir.suffix == '.log':
            raise TypeError('Input must be a directory of G16 log files or a single log file.')
        files = [parent_dir]    # Convert to list for later logic
    else:
        files = [x for x in parent_dir.glob('*.log')] # Get all the log files

    if len(files) == 0:
        raise FileNotFoundError(f'No log files found in {parent_dir.absolute()}')

    return files

def has_atomic_number_out_of_basis_set(split_text: list[str]) -> tuple[bool, str] | tuple[bool, None]:
    lines = [x for x in split_text if 'Atomic number out of range for' in x]
    if len(lines) != 0:
        return True, lines[0].strip()
    return False, None

def evaluate_g16_logfile(file: Path) -> tuple[Path, None, str] | tuple[Path, str, str] | tuple[Path, None, None]:
    '''
    Evaluates a Gaussian16 log file to determine whether it completed successfully,
    encountered an error, or terminated abnormally.

    Parameters
    ----------
    file : Path
        Path to the Gaussian16 .log file to be analyzed.

    Returns
    ----------
    tuple[Path, None, str]
        If the logfile completed successfully, returns the file path and its text.

    tuple[Path, str, str]
        If the logfile encountered an error, returns the file path, an error message,
        and the file text.

    tuple[Path, None, None]
        If the logfile is incomplete or running, returns the file path and None values.
    '''
    try:
        text = get_file_text(file)
    except UnicodeDecodeError:
        return file, 'UNICODE DECODE ERROR. CHECK FILE MANUALLY', None

    split_text = text.split('\n')

    # Check for PREEMPTION
    if job_preempted(file):
        return file, 'was PREEMPTED', text

    # Check for CANCELLED
    if job_cancelled(file):
        return file, 'was CANCELLED by user', text

    # TODO this line is essentially ignored if a "failure" is detected by later logic
    #if not _is_logfile_complete(split_text):
    #    return file, 'is not a complete logfile. Is the job running?'

    # Get the lines at which jobs start
    # and normal termination lines appear
    job_lines = get_job_start_line_numbers(text)
    term_lines = get_termination_line_numbers(text)
    error_lines = get_job_error_line_numbers(text)

    atomic_number_out_of_range, out_of_range_line = has_atomic_number_out_of_basis_set(split_text=split_text)
    if atomic_number_out_of_range:
        return file, f'failed because {out_of_range_line}', text

    # Check if there is a freq section before
    # parsing the lowest frequency
    if has_frequency_section(text):
        lowest_freq_is_negative, lowest_freq_value = has_imaginary_frequency(text)
        if lowest_freq_is_negative:
            return file, f'has an imaginary frequency at {round(lowest_freq_value, 4)}', text

    # If a specific error can be identified
    # use the text of the line as the "reason"
    if len(error_lines) != 0:
        return file, '\t'.join([split_text[i].strip() + f' (line {i})' for i in error_lines]), text

    # Iterate over the lines that indicate a job started
    for i, job_start in enumerate(job_lines):

        # Check if a termination line proceeded the job start line
        try:
            if job_start > term_lines[i]:
                return file, f'job on line {job_start + 1} failed.', text
        except IndexError:
            return file, f'job on line {job_start + 1} failed.', text

    #TODO
    #is_oscillating, oscillations = check_oscillating_optimization_criteria(text)

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

        print(f'{bcolors.OKGREEN}{file.name}{bcolors.ENDC}')
        if not args.dry:
            shutil.move(parent_dir / file.name, completed_dir / file.name)

        if file.with_suffix('.com').exists():
            print(f'{bcolors.OKGREEN}{file.with_suffix(".com").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".com").name, completed_dir / file.with_suffix(".com").name)

        if not args.deletechk:
            if file.with_suffix('.chk').exists():
                print(f'{bcolors.OKGREEN}{file.with_suffix(".chk").name}{bcolors.ENDC}')
                if not args.dry:
                    shutil.move(parent_dir / file.with_suffix(".chk").name, completed_dir / file.with_suffix(".chk").name)

    print('-------------------------FILES MOVED TO FAILED DIRECTORY------------------------')
    for file in failed.keys():

        print(f'{bcolors.FAIL}{file.name}{bcolors.ENDC}')
        if not args.dry:
            shutil.move(parent_dir / file.name, failed_dir / file.name)

        if file.with_suffix('.com').exists():
            print(f'{bcolors.FAIL}{file.with_suffix(".com").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".com").name, failed_dir / file.with_suffix(".com").name)

        if not args.deletechk:
            if file.with_suffix('.chk').exists():
                print(f'{bcolors.FAIL}{file.with_suffix(".chk").name}{bcolors.ENDC}')
                if not args.dry:
                    shutil.move(parent_dir / file.with_suffix(".chk").name, failed_dir / file.with_suffix(".chk").name)

    if delete_chk:
        print('-------------------------------DELETING CHK FILES-------------------------------')
        for file in failed.keys():
            chk_file = file.with_suffix('.chk')
            if chk_file.exists():
                print(chk_file.name)
                chk_file.unlink()

        for file in completed:
            chk_file = file.with_suffix('.chk')
            if chk_file.exists():
                print(chk_file.name)
                chk_file.unlink()

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
    files = get_logfiles(parent_dir)

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
            results = p.map(evaluate_g16_logfile, files)
            completed = [x[0] for x in results if x[1] is None]
            failed = {x[0]: x[1] for x in results if x[1] is not None}
    else:
        for file in files:

            file, logfile_assessment, file_text = evaluate_g16_logfile(file)

            if args.line_by_line:
                if file_text is None:
                    print(f'Could not perform line-by-line analysis because {logfile_assessment}')
                else:
                    print_line_by_line_analysis(file, file_text)

            if logfile_assessment is None and file not in failed.keys():
                completed.append(file)
            else:
                failed[file] = logfile_assessment

    print_summary(failed,
                  completed=completed,
                  files=files)

    # Print out the overall analysis
    if not args.dry:
        print_analysis_and_move_files(failed,
                                      completed=completed,
                                      files=files,
                                      parent_dir=parent_dir,
                                      delete_chk = bool(args.deletechk))

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