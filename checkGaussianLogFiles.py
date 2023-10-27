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

from pathlib import Path

try:
    import psutil
    proc = psutil.Process()
    proc.cpu_affinity([proc.cpu_affinity()[0]])
except ModuleNotFoundError:
    pass

DESCRIPTION = '🦝 Analyzes Gaussian 16 log files for common errors 🦝.'

LINK_PATTERN = re.compile(r' Entering Link\s+\d+', re.DOTALL)
NORM_TERM_PATTERN = re.compile(r' Normal termination of Gaussian 16', re.DOTALL)
PROCEDING_JOB_STEP_PATTERN = re.compile(r'\s+Link1:\s+Proceeding to internal job step number\s+', re.DOTALL)
FILEIO_ERROR_NON_EXISTENT_FILE = re.compile(r'\s+FileIO operation on non-existent file', re.DOTALL)
ERRORNEOUS_WRITE = re.compile(r'Erroneous write. Write\s+(-|)\d+\s+instead of \d+.',  re.DOTALL)
FREQ_START_PATTERN = re.compile(r'(?<=\n Frequencies --)(.*?)(?=\n Red. masses --)', re.DOTALL)
N_STEPS_EXCEEDED = re.compile(r'\s+--\s+Number of steps exceeded,\s+NStep= \d+')

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

    parser.add_argument('--dry',
                        action='store_true',
                        help='Disables creation of directories and file movement\n\n')

    parser.add_argument('--deletechk',
                        action='store_true',
                        help='Deletes ALL large .chk files that have a corresponding log instead of moving them.\n\n')

    args = parser.parse_args()

    return args

def get_file_text(file: Path) -> str:
    '''
    Gets the raw text from the file.
    '''
    with open(file, 'r') as infile:
        return infile.read()

def get_job_start_line_numbers(text: str) -> list[int]:
    '''
    Gets the line numbers that indicate a new link
    or an internal job. Successful calculations should
    have a "Normal termination" line after each of these.
    '''
    lines = text.split('\n')

    # Lines after which a normal termination should appear
    termination_indicator_lines = []

    for i, line in enumerate(lines):
        if re.match(LINK_PATTERN, line) is not None:
            termination_indicator_lines.append(i)
        elif re.match(PROCEDING_JOB_STEP_PATTERN, line) is not None:
            termination_indicator_lines.append(i)
        else:
            pass

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

def has_imaginary_frequency(text: str) -> bool:
    '''
    Determines if log file has imaginary frequencies
    '''
    return float(re.split('\s+', re.search(FREQ_START_PATTERN, text).group().strip())[0]) <= 0

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

def get_slurm_out_file(file: Path) -> Path:
    files = [x for x in file.parent.glob('*out*') if file.stem in x.name]

    # Check if only one output file exists
    if len(files) != 1:
        print(f'{bcolors.FAIL}WARNING: Multiple SLURM output files identified for {file.name}.{bcolors.ENDC}')

    return files[0]

def job_preempted(file: Path) -> bool:
    with open(get_slurm_out_file(file), 'r') as infile:
        lines = infile.readlines()

    if 'PREEMPTION' in lines[-1]:
        return True
    return False

def main(args) -> None:

    # Note the time
    t1 = time.time()

    # Input parsing
    if args.input is None:
        parent_dir = Path().cwd()
    else:
        parent_dir = Path(args.input)

    # Check if its a single file
    if not parent_dir.is_dir():
        if not parent_dir.suffix == '.log':
            raise TypeError('Input must be a directory of G16 log files or a single log file.')
        files = [parent_dir]    # Convert to list for later logic
    else:
        files = [x for x in parent_dir.glob('*.log')] # Get all the log files

    if len(files) == 0:
        raise FileNotFoundError(f'No log files found in {parent_dir.absolute()}')

    # Sort into failed dicts with files as
    # keys and reasons as values. Completed
    # is just a list of Paths
    failed = {}
    completed = []
    print(f'Analyzing {len(files)} files...')

    if len(files) >= 200:
        print(f'This may take a minute.')

    for file in files:

        # Check if preempted
        if job_preempted(file):
            failed[file] = 'was preempted.'
            continue

        # Get the file text
        text = get_file_text(file)
        split_text = text.split('\n')

        if args.debug:
            print_line_by_line_analysis(file, text)

        # TODO this line is essentially ignored if a "failure" is detected by later logic
        if not _is_logfile_complete(split_text):
            failed[file] = 'is not a complete logfile. Is the job running?'

        # Get the lines at which jobs start
        # and normal termination lines appear
        job_lines = get_job_start_line_numbers(text)
        term_lines = get_termination_line_numbers(text)
        error_lines = get_job_error_line_numbers(text)

        # Check if there is a freq section before
        # parsing the lowest frequency
        if has_frequency_section(text):
            if has_imaginary_frequency(text):
                failed[file] = 'has an imaginary frequency'
                continue

        # If a specific error can be identified
        # use the text of the line as the "reason"
        if len(error_lines) != 0:
            for i in error_lines:
                failed[file] = split_text[i].strip() + f' (line {i})'
                break
            continue

        # Iterate over the lines that indicate a job started
        for i, job_start in enumerate(job_lines):

            # Check if a termination line proceeded the job start line
            try:
                if job_start > term_lines[i]:
                    failed[file] = f'job on line {job_start+1} failed.'
            except IndexError:
                failed[file] = f'job on line {job_start+1} failed.'

        # Check if the logic above put the file
        # in the failed dict. If it didnt, it must
        # have completed
        if file not in failed.keys():
            completed.append(file)

    print('------------------------------------OVERVIEW------------------------------------')
    if len(failed) != 0:
        for file, reason in failed.items():
            print(f'{bcolors.FAIL}{file.name}{bcolors.ENDC} failed because {reason}')

    print('\n')
    print(f'{bcolors.BOLD}TOTAL{bcolors.ENDC}:\t\t{len(files)}')
    print(f'{bcolors.BOLD}COMPLETED{bcolors.ENDC}:\t{len(completed)} ({len(completed)} of {len(files)})')
    print(f'{bcolors.BOLD}FAILED{bcolors.ENDC}:\t\t{len(failed)} ({len(failed)} of {len(files)})')
    print('\n')

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

    if args.deletechk:
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

    if args.debug:
        print(f'Total time (s): {round(time.time() - t1,2)}')

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
            print(f'EXITING')
            exit()

    main(args)