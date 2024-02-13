:: Find the root path for the anaconda installation
IF EXIST %LOCALAPPDATA%\Continuum\miniconda3\ SET root=%LOCALAPPDATA%\Continuum\miniconda3\
IF EXIST %LOCALAPPDATA%\Continuum\anaconda3\ SET root=%LOCALAPPDATA%\Continuum\anaconda3\
IF EXIST %LOCALAPPDATA%\miniconda3 SET root=%LOCALAPPDATA%\miniconda3\
IF EXIST C:\Users\%USERNAME%\miniconda3 SET root=C:\Users\%USERNAME%\miniconda3\
IF EXIST C:\ProgramData\Anaconda3 SET root=C:\ProgramData\Anaconda3\
IF EXIST C:\Users\%USERNAME%\Anaconda3 SET root=C:\Users\%USERNAME%\Anaconda3\
CALL %root%Scripts\activate.bat %root%
:: remove then create the windfarmerAutomation conda environment
conda remove --name wf_auto --all --yes
conda env create -f environment.yml
conda activate wf_auto