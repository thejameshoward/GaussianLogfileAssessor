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

-  Run the script on different directory containing your G16 log files without moving any files using the `--dry` flag (recommended).

    ```checkGaussianLogFiles.py -i data/ --dry```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/example.png?raw=true)

-  Run the same analysis and move files into respective directories.

    ```checkGaussianLogFiles.py -i data/```

-  Request printout of detailed analysis of each file

    ```checkGaussianLogFiles.py -i data/ --line-by-line```

-  Run the analysis on a single .log file

    ```checkGaussianLogFiles.py -i data/james.log --debug --dry```

-  Delete .chk files that have a corresponding completed .log file (EXPERIMENTAL)

    ```checkGaussianLogFiles.py -i data/ --debug --deletechk```

-  Use multiprocessing to process files much faster (>10x speedup).<br>

> [!NOTE]
> This will use multiple processors and upset any resource allocation manager (Arbiter 2) on a shared systems. These should be run on compute nodes with at least 8 cores. <br>

    ```checkGaussianLogFiles.py -i data/ --parallel```

## CLI Flags

```-i, --input```&nbsp;&nbsp;&nbsp;&nbsp;The directory to be analyzed. The default is current working directory.

```-p, --parallel```&nbsp;&nbsp;&nbsp;&nbsp;Enables multiprocessing.

```--dry```&nbsp;&nbsp;&nbsp;&nbsp;Disable the creation of new folders and moving files. Useful for inspecting files.

```--debug```&nbsp;&nbsp;&nbsp;&nbsp;Prints extra debug information.

```--line-by-line```&nbsp;&nbsp;&nbsp;&nbsp;Prints detailed file and debug information to the terminal.

```--deletechk```&nbsp;&nbsp;&nbsp;&nbsp;Deletes .chk files of log files for both completed and not completed jobs (EXPERIMENTAL).