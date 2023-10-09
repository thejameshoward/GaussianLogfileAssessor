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

import pandas as pd
import numpy as np

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

periodictable = ["Bq","H","He","Li","Be","B","C","N","O","F","Ne","Na","Mg","Al","Si","P","S","Cl","Ar","K","Ca","Sc","Ti","V","Cr","Mn","Fe","Co","Ni","Cu","Zn","Ga","Ge","As","Se","Br","Kr","Rb","Sr","Y","Zr",
             "Nb","Mo","Tc","Ru","Rh","Pd","Ag","Cd","In","Sn","Sb","Te","I","Xe","Cs","Ba","La","Ce","Pr","Nd","Pm","Sm","Eu","Gd","Tb","Dy","Ho","Er","Tm","Yb","Lu","Hf","Ta","W","Re","Os","Ir","Pt","Au","Hg","Tl",
             "Pb","Bi","Po","At","Rn","Fr","Ra","Ac","Th","Pa","U","Np","Pu","Am","Cm","Bk","Cf","Es","Fm","Md","No","Lr","Rf","Db","Sg","Bh","Hs","Mt","Ds","Rg","Uub","Uut","Uuq","Uup","Uuh","Uus","Uuo","X"]

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

def get_ir_dataframe(file: Path,
          debug: bool = False,
          return_freq: bool = False) -> pd.DataFrame:
    '''
    A and B are atom NUMBERS not indices (so you have to subtract one in the code) or
    if you know you atom indices, just add one.

        Makes a molfile in the same directory as another filetype
    Currently supports .log and .xyz files.

    Parameters
    ----------
    file: Path
        The path to the Gaussian16 logfile

    return_freq: bool
        If true, the frequency of the selected IR vibration is returned
        instead of the entire frequency dataframe. In this case, the function
        checks that there is exactly one frequency.

    Returns
    ----------
    pd.DataFrame
    '''
    # where the freqs begin
    frqs_pattern = re.compile("Red. masses")

    # where the freqs end
    frqsend_pattern = re.compile("Thermochemistry")

    filecont = get_file_text(file)

    frq_len = 0
    frq_end = 0

    found = False

    # James added this, it's a lot cleaner, but it breaks code in the future!
    for i, line in enumerate(filecont):
        if frqs_pattern.search(line) and not found:
            frq_start = i - 3
            found = True
            if debug: print(f'Found start of frequencies on line {frq_start + 1}')
        if frqs_pattern.search(line) and found and frq_len == 0: # This logic skips calculating the frq_len if we just found the pattern. Avoids setting frq_len = 0
            frq_len = i - 3 - frq_start
        if frqsend_pattern.search(line) and found:
            if debug: print(f'Found end of frequencies on line {i + 1}')
            frq_end = i - 3
            break

    if debug:
        print(f'The length of the frq block is {frq_len}')

    blocks = int((frq_end + 1 - frq_start) / frq_len)

    if debug:
        print(f'Number of blocks: {blocks}\n')

    # list of IR_calculator objects. IR contains: IR.freq, IR.int, IR.deltas = []
    data = []

    for i in range(blocks):
        for j in range(len(filecont[i * frq_len + frq_start].split())):

            data.append(IR_calculator(file, i * frq_len + frq_start, j, frq_len))

    if debug: print(f'Number of IR Frequencies {len(data)}\n')

    # Get a list of IR frequencies for the indicated atoms and put it into a dataframe
    freqs = [
        IR_frequency(
            delta_atom_A = z.deltas[A-1],
            delta_atom_B = z.deltas[B-1],
            atom_A_symbol = z.elements[A-1],
            atom_B_symbol = z.elements[B-1],
            frequency = z.freq,
            intensity = z.int,
            delta_vector_atom_A = z.delta_vectors[A-1],
            delta_vector_atom_B = z.delta_vectors[B-1],
            stretch=z._is_stretch(A,B)
                    ).__dict__ for z in data]

    IR_frequencies = pd.DataFrame(freqs)

class IR_frequency:
    '''
    Class for an IR frequency result
    '''

    def __init__(
        self,
        delta_atom_A: float,
        delta_atom_B: float,
        atom_A_symbol: str,
        atom_B_symbol: str,
        frequency: float,
        intensity: float,
        delta_vector_atom_A: list = None,
        delta_vector_atom_B: list = None,
        stretch: bool = None) -> None:

        self.delta_atom_A = delta_atom_A
        self.delta_atom_B = delta_atom_B
        self.atom_A_symbol = atom_A_symbol
        self.atom_B_symbol = atom_B_symbol
        self.frequency = frequency
        self.intensity = intensity
        self.stretch = stretch


        # This only tells you if the atoms are moving away from eachother, not
        # whether they are moving away from eachother along the bond axis
        #TODO Determine whether the motion happens along the axis of a bond
        if delta_vector_atom_A is not None and delta_vector_atom_B is not None:

            # Get the angle betwee the two vectors
            self.motion_angle = np.arccos(np.clip(np.dot(self._unit_vec(delta_vector_atom_A), self._unit_vec(delta_vector_atom_B)), -1.0, 1.0)) * 57.2958

    def _unit_vec(self, vector):
        '''Calculates the unit vector for an input vector'''
        return vector / np.linalg.norm(vector)

class IR_calculator:
    '''
    Takes the filecontents, start_line of the frequency 3 frequencies of interest, column of the frequency
    and the length of the frequency block to generate a single dataset which represents the vibration
    '''
    def __init__(
        self,
        filecontent: list[str],
        start_line,
        col,
        frq_len):

        # start_line contains the frequency number, split method makes 3-item list
        self.freqno = int(filecontent[start_line].split()[col])
        # Add 2 to get to the frequency line, add two to col because the split method makes a 5-item list
        self.freq = float(filecontent[start_line + 2].split()[col + 2])
        # Add 5 to get to the intensity line, add three to col because the split method makes a 5-item list
        self.int = float(filecontent[start_line + 5].split()[col + 3])

        # List of atom motion distances
        self.deltas = []
        self.delta_vectors = []

        atomnos = []

        # TO-DO: Understand this logic
        for a in range(frq_len - 7):
            atomnos.append(filecontent[start_line +7+a].split()[1])
            x = float(filecontent[start_line + 7 + a].split()[3 * col + 2])
            y = float(filecontent[start_line + 7 + a].split()[3 * col + 3])
            z = float(filecontent[start_line + 7 + a].split()[3 * col + 4])

            self.deltas.append(np.linalg.norm([x,y,z]))
            self.delta_vectors.append([x,y,z])

        self.elements = [periodictable[int(a)] for a in atomnos]

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

            # Print the debug information
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
        error_lines = get_job_error_line_numbers(text)

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

        # Check for imaginary frequencies
        if file not in failed.keys():
            print(get_ir_dataframe(file, debug=True))
        print('a')
        exit()

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

        # Move the com
        if file.with_suffix('.com').exists():
            print(f'{bcolors.OKGREEN}{file.with_suffix(".com").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".com").name, completed_dir / file.with_suffix(".com").name)

        # Move the chk
        if file.with_suffix('.chk').exists():
            print(f'{bcolors.OKGREEN}{file.with_suffix(".chk").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".chk").name, completed_dir / file.with_suffix(".chk").name)

        # Move the fchk
        if file.with_suffix('.fchk').exists():
            print(f'{bcolors.OKGREEN}{file.with_suffix(".fchk").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".fchk").name, completed_dir / file.with_suffix(".fchk").name)

    print('-------------------------FILES MOVED TO FAILED DIRECTORY------------------------')
    for file in failed.keys():

        print(f'{bcolors.FAIL}{file.name}{bcolors.ENDC}')
        if not args.dry:
            shutil.move(parent_dir / file.name, failed_dir / file.name)

        # Move the com
        if file.with_suffix('.com').exists():
            print(f'{bcolors.FAIL}{file.with_suffix(".com").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".com").name, failed_dir / file.with_suffix(".com").name)

        # Move the chk
        if file.with_suffix('.chk').exists():
            print(f'{bcolors.FAIL}{file.with_suffix(".chk").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".chk").name, completed_dir / file.with_suffix(".chk").name)

        # Move the fchk
        if file.with_suffix('.fchk').exists():
            print(f'{bcolors.FAIL}{file.with_suffix(".fchk").name}{bcolors.ENDC}')
            if not args.dry:
                shutil.move(parent_dir / file.with_suffix(".fchk").name, completed_dir / file.with_suffix(".fchk").name)

if __name__ == "__main__":
    args = get_args()

    main(args)