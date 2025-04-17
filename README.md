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

-  Run the script on __different__ directory containing the `.log` files without moving any files using the `--dry` flag (recommended).

    ```checkGaussianLogFiles.py -i data/ --dry```

-  Run the same analysis and move files into respective directories.

    ```checkGaussianLogFiles.py -i data/```

-  Request printout of detailed analysis of each file

    ```checkGaussianLogFiles.py -i data/ --line-by-line```

-  Run the analysis on a single .log file

    ```checkGaussianLogFiles.py -i data/james.log --dry```

-  Delete .chk files that have a corresponding completed .log file (EXPERIMENTAL)

    ```checkGaussianLogFiles.py -i data/ --deletechk```

-  Use multiprocessing to process files much faster (>10x speedup).

    ```checkGaussianLogFiles.py -i data/ --parallel```

> [!NOTE]
> The command above will use multiple processors and upset any resource allocation manager (e.g., Arbiter 2) on shared systems.
> These should be run on compute nodes with at least 8 cores.



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