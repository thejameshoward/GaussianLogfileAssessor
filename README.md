# GaussianLogfileAssessor
Analyzes Gaussian .log files


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

## Example usage

1.  Run the script in the directory containing your Gaussian 16 log files.

    ```checkGaussianLogFiles.py```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/example.png?raw=true)

2.  Run the script on a directory containing your Gaussian 16 log files without copying files.

    ```checkGaussianLogFiles.py -i data/ --dry```

3.  Enable detailed analysis of each file.

    ```checkGaussianLogFiles.py -i data/ --debug```

    ![example usage](https://github.com/thejameshoward/GaussianLogfileAssessor/blob/master/img/verbose.png?raw=true)