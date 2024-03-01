# WindFarmer Automation 
A repository for to share some standard WindFarmer automation python examples and the dependencies required to run them.

# Setup your workspace to automate WindFarmer

## Clone this repository
Download a local clone of this repository using Git. Git can be downloaded from [here](https://git-scm.com/download/win).

Open a Git bash terminal where you would like the repository to be saved (e.g. ```C:\Repos```) then run:
```
git clone http://tfs.stp.dnvgl.com:8080/tfs/DefaultCollection/PlanningTools/_git/WindFarmerAutomation
```

## Install Miniconda Python
Our demonstrations are built on top of miniconda. This is a minimal, free distribution of python:
Install for Windows from: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe 

## Create the WindFarmer automation python environment
We will use a conda environment to ensure that you have all the necessary dependencies to run WindFarmer Automation examples.

For a quick setup, run the ```Source\create_wf_auto_env.bat``` file (double click on it within file explorer) to create the wf_auto environment. 

Alternatively open anaconda prompt, cd into the ```Source``` folder and create the environement defined in the ```environment.yml``` file with the following command:
```
conda env create -f environment.yml
```

## Install the windfarmer python package
The source folder contains the windfarmer python package code. Currently this only has one function to connect to the WindFarmer python SDK. To run our python SDK examples you must build this package and install it to use it within other scripts. 
1. Open the file ```Source\build_and_install.bat``` and edit line 2 to be the location of the ```Source``` folder on your machine. 
2. Copy-paste the contents of this file into a command prompt window (Start menu > type cmd.exe and open)
3. Hit return and close cmd.exe
4. Now you should have the windfarmer package installed into the wf_auto environment. You can check this worked correctly by running a simple script to test importing the package: Tests\test_windfarmer_Sdk.py

## Setup your python IDE: Visual studio code
Feel free to use the IDE of your choice, but we will use Visual studio Code in our examples. 

Install VS Code for free from: https://code.visualstudio.com/

Next, install the Python extension for VS Code from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=ms-python.python). The Python extension is named Python and it's published by Microsoft.

### Choose the Python environment
In VS code use Ctrl+Shift+P to open the Command Pallete they type "Python: Select Interpreter". Select wf_auto to activate it for demos. 

For notebooks you may be asked what environment to use first time you run, or you can select in the top right of the interpreter.  
 
For python scripts, the environment is shown bottom right of the UI.
 
### Set a default python environment
If you'd like to set up a default interpreter in VS code to use at startup, you can edit the entry for ```python.defaultInterpreterPath``` manually inside your User Settings. To do so, open the Command Palette (Ctrl+Shift+P) and enter Preferences: Open User Settings. Find then set python.defaultInterpreterPath to the location of your prefered interpreter.
