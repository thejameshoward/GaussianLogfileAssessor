#!/usr/bin/env python3
# coding: utf-8

'''
Analyzes Gaussian .log files
'''

from __future__ import annotations

import re
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
    termination_indicator_lines = []

    # Get number of links/terminations
    n_links = get_n_links(text)
    n_term = get_n_normal_terminations(text)

    print(f'\tNumber of link statements\t\t{n_links}')
    print(f'\tNumber of termination statements:\t{n_term}\n')
    print('\tLine-by-line analysis:')
    for i, line in enumerate(lines):
        if re.match(LINK_PATTERN, line) is not None:
            print(f'\t\tLINK\t\t{i+1}')
            termination_indicator_lines.append(i)

        elif re.match(NORM_TERM_PATTERN, line) is not None:
            print(f'\t\tNORM TERM\t{i+1}')

        elif re.match(PROCEDING_JOB_STEP_PATTERN, line) is not None:
            print(f'\t\tINTERNAL JOB\t{i+1}')
            termination_indicator_lines.append(i)
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
    return False

def main(args) -> None:
    if args.input is None:
        parent_dir = Path().cwd()
    else:
        parent_dir = Path(args.input)

    # Check if its a single file
    if not parent_dir.is_dir():
        raise TypeError(f'{parent_dir.absolute()} is not a directory.')

    # Get all the log files
    files = [x for x in parent_dir.glob('*.log')]

    if len(files) == 0:
        raise FileNotFoundError(f'No log files found in {parent_dir.absolute()}')

    if args.debug:
        # Process the files
        for file in files:
            # For printing headers
            len_file_name = len(file.name)
            spacer = (80 - len_file_name) / 2
            print('-'* math.ceil(spacer) + file.name + '-'* math.floor(spacer))

            # Get the file text
            text = get_file_text(file)

            process_text(text)

            print('\n')


    # Sort into failed dicts with files as
    # keys and reasons as values
    failed = {}
    completed = []
    for file in files:
        # Get the file text
        text = get_file_text(file)

        # Get the lines at which jobs start
        # and normal termination lines appear
        term_lines = get_termination_line_numbers(text)
        job_lines = get_job_start_line_numbers(text)

        # iterate over the lines that
        for i, job_start in enumerate(job_lines):

            # If the job start line is not proceeded by
            # a normal termination line, that job failed
            try:
                if job_start > term_lines[i]:
                    failed[file] = f'Job on line {job_start+1} failed.'
            except IndexError:
                failed[file] = f'Job on line {job_start+1} failed'


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

    print('-------------------------FILES MOVED TO FAILED DIRECTORY------------------------')
    for file in failed.keys():

        print(f'{bcolors.FAIL}{file.name}{bcolors.ENDC}')
        if not args.dry:
            shutil.move(parent_dir / file.name, failed_dir / file.name)

        if file.with_suffix('.com').exists():
            print(f'{bcolors.FAIL}{file.with_suffix(".com").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".com").name, failed_dir / file.with_suffix(".com").name)

if __name__ == "__main__":
    args = get_args()

    main(args)