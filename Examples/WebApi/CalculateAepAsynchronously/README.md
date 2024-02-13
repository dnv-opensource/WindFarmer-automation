# Batch calculate Annual Energy Production using the web API

This batch of scripts demonstrates how you may go from a WindFarmer desktop setup through to using the WindFarmer web API. 

## Demo summary
1. Web API input json files are generated for every layout scenario in  every workbook in a folder of WindFarmer Workbooks using the windfarmer SDK. 
2. Annual energy production is computed for each scenario input JSON file using, calling the AEP API asynchronously. 

## 01_get_aep_api_inputs_from_workbook.py

Edit or check the user inputs noted below then run the script. 

| User inputs to edit| notes   |
|--------------------|---------|
| ```windfarmer_binary_path``` | Identify the installation folder for the version of WindFarmer you wish to use. |
| ```workbook_folder_path``` | # Identify a folder containing WindFarmer workbooks (.wwx files) |

Outputs will by default be written to the folder AEPInputsJson, within this folder. Two example JSON files are already provided in this folder, in case you wish to only run the AEP API script 02 without having to construct WindFarmer workbooks. 

## 02_compute_AEP_async.py

This is a basic example of how to call the AEP Asynchronously. Assuming the AEPInputsJson folder contains AEP input json files you can run this script with the following user inputs:

| User inputs to edit| notes   |
|--------------------|---------|
|WINDFARMER_ACCESS_KEY | The name of the environment variable used to store your access key. See ```Examples\WebAPI\README.md``` and the section **Environment variable to store API access key** for how to user environment variables. |