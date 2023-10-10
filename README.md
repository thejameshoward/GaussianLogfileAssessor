# GaussianLogfileAssessor
This script provides useful information about Gaussian 16 .log files including whether or not all planned calculations (or internal Gaussian jobs) completed. By default, the script moves the completed and failed fails along with any corresponding input (.com) files to their respective `failed` and `completed` directories.
<br>
<br>


## Installation
1.  Clone the repository. This can be deleted after completing all steps.

    ```git clone https://github.com/thejameshoward/GaussianLogfileAssessor.git```

2.  Make the assessment script executable.

    ```chmod +x GaussianLogfileAssesor/checkGaussianLogFiles.py```

3.  Copy the assessment script to a directory on your PATH environment variable.

    ```cp GaussianLogfileAssesor/checkGaussianLogFiles.py ~/bin/```

4.  That's it!

In the example above, ~/bin/ is an existing directory on the PATH. If you have not added<br>
a directory to PATH, see [https://askubuntu.com/questions/402353/how-to-add-home-username-bin-to-path](https://askubuntu.com/questions/402353/how-to-add-home-username-bin-to-path).

## Examples

1.  Run the script on different directory containing your Gaussian 16 log files without moving any files (recommended).

    ```checkGaussianLogFiles.py -i data/ --dry```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/example.png?raw=true)

2.  Run the same analysis and move files into respective directories.

    ```checkGaussianLogFiles.py -i data/```

3.  Enable detailed analysis of each file.

    ```checkGaussianLogFiles.py -i data/ --debug```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/verbose.png?raw=true)

3.  Enable the deletion of .chk files that have a corresponding .log file (EXPERIMENTAL)

    ```checkGaussianLogFiles.py -i data/ --debug --deletechk```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/verbose.png?raw=true)

## CLI Flags

```-i, --input```&nbsp;&nbsp;&nbsp;&nbsp;The directory to be analyzed. The default is current working directory.

```--dry```&nbsp;&nbsp;&nbsp;&nbsp;Disable the creation of new folders and moving files. Useful for inspecting files.

```--debug```&nbsp;&nbsp;&nbsp;&nbsp;Enables dev level debugging to be printed to the terminal.

```--deletechk```&nbsp;&nbsp;&nbsp;&nbsp;Deletes .chk files of log files for both completed and not completed jobs (EXPERIMENTAL).