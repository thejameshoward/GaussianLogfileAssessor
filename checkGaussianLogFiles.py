#!/usr/bin/env python3
# coding: utf-8

'''
Analyzes Gaussian .log files
'''

from __future__ import annotations

import re

import argparse

from pathlib import Path

import psutil
proc = psutil.Process()
proc.cpu_affinity([proc.cpu_affinity()[0]])

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

    for i, line in enumerate(lines):
        if re.match(LINK_PATTERN, line) is not None:
            print(f'\tLink on line {i+1}')
            termination_indicator_lines.append(i)

        elif re.match(NORM_TERM_PATTERN, line) is not None:
            print(f'\tTermination on line {i+1}')

        elif re.match(PROCEDING_JOB_STEP_PATTERN, line) is not None:
            print(f'\tStarted internal job step on line {i+1}')
            termination_indicator_lines.append(i)
        else:
            pass

    print(termination_indicator_lines)

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

    if args.debug:
        # Process the files
        for file in files:
            # For printing headers
            len_file_name = len(file.name)
            spacer = (80 - len_file_name) / 2
            print('-'* int(spacer), file.name, '-'* int(spacer))

            # Get the file text
            text = get_file_text(file)

            # Get number of links/terminations
            n_links = get_n_links(text)
            n_term = get_n_normal_terminations(text)

            print(f'\tNumber of link statements\t\t{n_links}')
            print(f'\tNumber of termination statements:\t{n_term}')

            process_text(text)

            print('-'*80)


    # Sort into failed dicts with files as
    # keys and reasons as values
    failed = {}
    completed = []
    for file in files:
        # Get the file text
        text = get_file_text(file)

        # Get number of links/terminations
        n_links = get_n_links(text)
        n_term = get_n_normal_terminations(text)

        if n_term < n_links:
            failed[file] = 'N_TERMINATION < N_LINKS'
            #print(f'{file.name}\tTERMINATIONS < LINKS ({n_term} < {n_links})')
        elif has_imaginary_frequency(text):
            failed[file] = 'imaginary frequency'
        else:
            completed.append(file)

    if len(failed) != 0:
        for file, reason in failed.items():
            print(f'{file.name} failed because {reason}')
    else:
        print(f'{bcolors.OKGREEN}No Gaussian logfile jobs failed.{bcolors.ENDC}')


if __name__ == "__main__":
    args = get_args()

    main(args)