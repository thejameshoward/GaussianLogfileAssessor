# GaussianLogfileAssessor
This script analyzes and reports information about Gaussian 16 (G16) .log files including whether or not all planned calculations (or internal Gaussian jobs) terminated successfully. By default, the script moves the completed and failed .log, .com, and .chk files to their respective `failed` and `completed` directories.
<br>
<br>


## Installation
1.  Clone the repository. This can be deleted after completing all steps.

    ```git clone https://github.com/thejameshoward/GaussianLogfileAssessor.git```

2.  Make the assessment script executable.

    ```chmod +x GaussianLogfileAssessor/checkGaussianLogFiles.py```

3.  Copy the assessment script to a directory on your PATH environment variable.

    ```cp GaussianLogfileAssesor/checkGaussianLogFiles.py ~/bin/```

4.  That's it!

In the example above, ~/bin/ is an existing directory on the PATH. If you have not added<br>
a directory to PATH, see [https://askubuntu.com/questions/402353/how-to-add-home-username-bin-to-path](https://askubuntu.com/questions/402353/how-to-add-home-username-bin-to-path).

## Examples
The simplest way to use this script is the `cd` into the directory that contains the `.log` files. The other files associated with G16 calculations (`.com`, `.chk`, etc.) do not have to be present, although they are recognized and moved by the program into `failed` and `completed` directories. After running `cd` into the directory
containing your `.log` files, run the script with the dry flag first to run the analysis. No files will be moved or deleted.

-  Run the analysis in the current working directory without moving files (note that the `-i` flag is not specified)

    ```checkGaussianLogFiles.py --dry```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/example.png?raw=true)

-  Run the same analysis in the current working directory, but this time, move files into `failed` and `completed` directories.

    ```checkGaussianLogFiles.py```

-  Run the same analysis and move files into respective directories.

    ```checkGaussianLogFiles.py -i data/```

-  Request printout of detailed analysis of each file

    ```checkGaussianLogFiles.py -i data/ --line-by-line```

-  Run the analysis on a single .log file

    ```checkGaussianLogFiles.py -i data/james.log --dry```

-  Use multiprocessing to process files much faster (>10x speedup).

    ```checkGaussianLogFiles.py -i data/ --parallel```

> [!NOTE]
> The command above will use multiple processors and upset any resource allocation manager (e.g., Arbiter 2) on shared systems.
> These should be run on compute nodes with at least 8 cores.

## How it works
checkGaussianLogFiles.py will check for an alternating pattern of calculation starts and completions. It is designed to detect both internal
jobs (e.g., frequency calculations) as well as additional jobs specified by the user in the input file. In addition to checking for errors
that happen within G16, the script will attempt to locate a .error file written by SLURM to check for errors that happen outside of G16. If
this file is not present, a specific reason for the job failing may not be provided and you will see errors like "<your_file>.log failed because
job on line 6 failed". This ambiguous message is printed by default if a specific reason is not found.
<br>
<br>
If you happen to find a specific error in G16 that is not identified in the current script, please open an issue on this repository and include the .log
file. Below is a list of errors currently identified by the script.
<br>
<br>
__SLURM errors detected__ (only found if a .error file is identified with your .log file)
1. Preemption
2. oom_kill events
3. Cancelled by user

__G16 errors detected__
1. Atomic number out of range for a particular basis set
2. Combination of multiplicity and number of electrons is impossible
3. Erroneous write errors (files moved or overwritten during calculation)
4. Negative vibration frequencies
5. Oscillating optimization criteria

## CLI Flags

```-h, --help```&nbsp;&nbsp;&nbsp;&nbsp;Print the help message

```-i, --input```&nbsp;&nbsp;&nbsp;&nbsp;The directory to be analyzed. The default is current working directory.

```--dry```&nbsp;&nbsp;&nbsp;&nbsp;Disable the creation of new folders and moving files. Useful for __just__ analyzing files.

```-p, --parallel```&nbsp;&nbsp;&nbsp;&nbsp;Enables multiprocessing.

```--line-by-line```&nbsp;&nbsp;&nbsp;&nbsp;Prints detailed file and debug information to the terminal.

```--deletechk```&nbsp;&nbsp;&nbsp;&nbsp;Deletes .chk files of log files for both completed and not completed jobs (EXPERIMENTAL).

```-t , --tolerance```&nbsp;&nbsp;&nbsp;&nbsp;Sets the tolerance value for determining oscillating optimizations (default=1e-5).

```-w , --window```&nbsp;&nbsp;&nbsp;&nbsp;Number of optimization steps to look at when evaluating oscillations (default=10).

```--no-oscillation-criteria```&nbsp;&nbsp;&nbsp;&nbsp;Disables detection of oscillations to increase assessment speed. Oscillations appear as ambiguous failed jobs.

```--debug```&nbsp;&nbsp;&nbsp;&nbsp;Prints extra debug information.