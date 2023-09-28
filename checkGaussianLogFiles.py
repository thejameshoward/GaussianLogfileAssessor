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

def get_file_text(file: Path) -> str:
    '''Gets the raw text from the file'''
    with open(file, 'r') as infile:
        return infile.read()

def process_text(text: str) -> None:
    lines = txt.split('\n')
    for line in lines:


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

    for file in files:
        text = get_file_text(file)




if __name__ == "__main__":

    args = get_args()
    main(args)