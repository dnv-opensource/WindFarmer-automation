# SDK automation examples
As an alternative to the built-in script editing user interface, the SDK enables you to automate WindFarmer from your preferred development environment (VSCode, Jupyter notebooks, PyCharm etc.), resulting in a more streamlined development process amenable to all professional software development practices.

The SDK enables you to link to and integrate WindFarmer into your existing software and tooling.

See [SDK introduction](https://mysoftware.dnv.com/download/public/renewables/windfarmer/manuals/latest/Automation/SDK/sdkIntro.html?tabs=Toolbox) in the WindFarmer online docs for more information on how to connect the SDK to WindFarmer. Alternative to those instructions, you could install a WindFarmer package as described below.

## Install the windfarmer python package
The source folder contains the windfarmer python package code. Currently this only has one function to connect to the WindFarmer python SDK. To run our python SDK examples you must build this package and install it to use it within other scripts. 
1. Open the file ```Source\build_and_install.bat``` and edit line 2 to be the location of the ```Source``` folder on your machine. 
2. Copy-paste the contents of this file into a command prompt window (Start menu > type cmd.exe and open)
3. Hit return and close cmd.exe
4. Now you should have the windfarmer package installed into the wf_auto environment. You can check this worked correctly by running a simple script to test importing the package: Tests\test_windfarmer_Sdk.py