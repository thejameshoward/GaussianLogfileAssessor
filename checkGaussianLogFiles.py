#!/usr/bin/env python3
# coding: utf-8

'''
Analyzes Gaussian .log files
'''

from __future__ import annotations
from multiprocessing.sharedctypes import Value

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

DESCRIPTION = 'None'

LINK_PATTERN = re.compile(r' Entering Link\s+\d+', re.DOTALL)
NORM_TERM_PATTERN = re.compile(r' Normal termination of Gaussian 16', re.DOTALL)
PROCEDING_JOB_STEP_PATTERN = re.compile(r'\s+Link1:\s+Proceeding to internal job step number\s+', re.DOTALL)
FILEIO_ERROR_NON_EXISTENT_FILE = re.compile(r'\s+FileIO operation on non-existent file', re.DOTALL)
ERRORNEOUS_WRITE = re.compile(r'Erroneous write. Write\s+(-|)\d+\s+instead of \d+.',  re.DOTALL)
FREQ_START_PATTERN = re.compile(r'(?<=\n Frequencies --)(.*?)(?=\n Red. masses --)', re.DOTALL)

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
                        help='Directory to analyze. (default=cwd)\n\n')

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
    '''Gets the raw text from the file'''
    with open(file, 'r') as infile:
        return infile.read()

def process_text(text: str) -> None:
    '''Detailed debugging info on a file'''
    lines = text.split('\n')

    # Lines after which a normal termination should appear
    calc_start_line = []

    # Get number of links/terminations
    n_links = get_n_links(text)
    n_term = get_n_normal_terminations(text)

    print(f'\tNumber of link statements\t\t{n_links}')
    print(f'\tNumber of termination statements:\t{n_term}\n')

    print('\tLine-by-line analysis:')
    for i, line in enumerate(lines):
        if re.match(LINK_PATTERN, line) is not None:
            print(f'\t\tENTER LINK\t\t\t{i+1}')
            calc_start_line.append(i)

        elif re.match(NORM_TERM_PATTERN, line) is not None:
            print(f'\t\tNORM TERM\t\t\t{i+1}')

        elif re.match(PROCEDING_JOB_STEP_PATTERN, line) is not None:
            print(f'\t\tENTER INTERNAL JOB\t\t\t{i+1}')
            calc_start_line.append(i)

        elif re.match(FILEIO_ERROR_NON_EXISTENT_FILE, line) is not None:
            print(f'\t\tFileIO Error (non-existent)\t{i+1}')

        elif re.match(ERRORNEOUS_WRITE, line) is not None:
            print(f'\t\tERRONEOUS WRITE\t\t\t{i+1}')

        else:
            pass

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

    # Lines after which a normal termination should appear
    error_lines = []

    for i, line in enumerate(lines):
        if re.match(FILEIO_ERROR_NON_EXISTENT_FILE, line) is not None:
            error_lines.append(i)

        elif re.match(ERRORNEOUS_WRITE, line) is not None:
            error_lines.append(i)

        else:
            pass

    return error_lines

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
        if re.match(NORM_TERM_PATTERN, line) is not None:
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
    freqs = re.findall(FREQ_START_PATTERN, text)

    if len(freqs) == 0:
        raise ValueError(f'File does not have any frequencies.')

    freqs = [re.sub('\s+', ' ', f).strip() for f in freqs]
    freqs = [re.split(' ', x) for x in freqs]
    freqs = [float(f) for freq_list in freqs for f in freq_list]
    if min(freqs) <= 0:
        return True
    return False

def has_frequency_section(text: str) -> bool:
    '''
    Determines if log file has a frequency section
    '''
    freqs = re.findall(FREQ_START_PATTERN, text)

    if len(freqs) == 0:
        return False

    return True

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

    # Detailed line-by-line analysis section
    if args.debug:
        # Process the files
        for file in files:
            # For printing headers
            len_file_name = len(file.name)
            spacer = (80 - len_file_name) / 2
            print('-'* math.ceil(spacer) + file.name + '-'* math.floor(spacer))

            # Get the file text
            text = get_file_text(file)

            # Print the debug information
            process_text(text)
            print('\n')

    # Sort into failed dicts with files as
    # keys and reasons as values. Completed
    # is just a list of Paths
    failed = {}
    completed = []
    print(f'Analyzing {len(files)} files...')
    if len(files) >= 200:
        print(f'This may take a minute.')
    for file in files:
        # Get the file text
        text = get_file_text(file)

        # Get the lines at which jobs start
        # and normal termination lines appear
        term_lines = get_termination_line_numbers(text)
        job_lines = get_job_start_line_numbers(text)
        error_lines = get_job_error_line_numbers(text)

        if has_frequency_section(text):
            if has_imaginary_frequency(text):
                failed[file] = 'Imaginary frequency'
                continue

        # iterate over the lines that indicate a job started
        for i, job_start in enumerate(job_lines):

            # If an error was found in the file
            # Before a job start line could be
            # proceeded by a normal termination line,
            # that job has failed because of the error line
            try:
                if job_start < error_lines[i]:
                    failed[file] = f'Job on line {job_start+i} had an error'
                    break
            except IndexError as e:
                pass

            # Check if a termination line proceeded the job start line
            try:
                if job_start > term_lines[i]:
                    failed[file] = f'Job on line {job_start+1} failed.'
            except IndexError:
                failed[file] = f'Job on line {job_start+1} failed.'

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
    print(f'TOTAL:\t\t{len(files)}')
    print(f'COMPLETED:\t{len(completed)} ({len(completed)} of {len(files)})')
    print(f'FAILED:\t\t{len(failed)} ({len(failed)} of {len(files)})')
    print('\n')

    if not args.dry:
        # Make the new folders
        completed_dir = parent_dir / 'completed'
        failed_dir = parent_dir / 'failed'
        completed_dir.mkdir()
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