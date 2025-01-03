# WindFarmer Automation 
This repository shares some WindFarmer automation examples and the dependencies required to run them, including demo data. Examples are included for:
1. Using the WindFarmer Automation module features that automate the WindFarmer desktop functions, either via
  * python automations with the SDK: [Examples\Sdk](./Examples/Sdk/README.md)
  * in-app automations using python or C#: [Examples\InApp](./Examples/InApp/README.md) 
2. Examples for calling the Web API to compute AEP or Blockage Corrections using DNV's cloud compute, including how to run the CFD.ML turbine interaction model calculations: [Examples\WebApi](./Examples/WebApi) 

## Clone this repository
You can download a local clone of this repository using Git. Git can be downloaded from [here](https://git-scm.com/download/win).

Open a Git bash terminal where you would like the repository to be saved (e.g. ```C:\Repos```) then run:
```
git clone https://github.com/dnv-opensource/WindFarmer-automation.git
```

## Setup required to run WindFarmer Desktop automations via the SDK
First see [Python setup](https://mysoftware.dnv.com/download/public/renewables/windfarmer/manuals/latest/Automation/SDK/pythonSetup.html), if you haven't already set up python tools to run the web API, then [SDK introduction](https://mysoftware.dnv.com/download/public/renewables/windfarmer/manuals/latest/Automation/SDK/sdkIntro.html) for more information on using the SDK.

## Setup required to run WindFarmer Web API automations
See [WindFarmer Services API - getting started](https://mysoftware.dnv.com/download/public/renewables/windfarmer/manuals/latest/WebAPI/Introduction/gettingStarted.html) for guidance on how to install the toolchain required to run web API automations, including:
a.	Software installation: an “IDE” for running Python scripts, and Python 
b.  Aquiring your web API access key
c.	Downloading the example scripts presented here
d.  Checking your Web API connection
