:: Edit the following path for your local machine
cd "C:\Repos\WindFarmerAutomation\Source"
:: Find the root path for the anaconda installation
IF EXIST %LOCALAPPDATA%\Continuum\miniconda3\ SET root=%LOCALAPPDATA%\Continuum\miniconda3\
IF EXIST %LOCALAPPDATA%\Continuum\anaconda3\ SET root=%LOCALAPPDATA%\Continuum\anaconda3\
IF EXIST %LOCALAPPDATA%\miniconda3 SET root=%LOCALAPPDATA%\miniconda3\
IF EXIST C:\Users\%USERNAME%\miniconda3 SET root=C:\Users\%USERNAME%\miniconda3\
IF EXIST C:\ProgramData\Anaconda3 SET root=C:\ProgramData\Anaconda3\
IF EXIST C:\Users\%USERNAME%\Anaconda3 SET root=C:\Users\%USERNAME%\Anaconda3\
CALL %root%Scripts\activate.bat %root%
:: Activate the automation conda environment
conda activate wf_auto
:: Build the wheel for the windfarmer package
python setup.py bdist_wheel --universal
:: Install the wheel in developer mode
pip install -e .
