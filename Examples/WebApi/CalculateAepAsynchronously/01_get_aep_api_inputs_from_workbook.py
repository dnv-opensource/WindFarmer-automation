#notebook to extract data web API input json files for scenarios in workbooks in a chosen folder
#%% User inputs - Connect to the WindFarmer desktop SDK
#  Identify the installation folder for the version of WindFarmer you wish to use. 
import windfarmer.sdk
windfarmer_installation_folder = r'C:\Program Files\DNV\WindFarmer - Analyst 1.5.4'
wf = windfarmer.sdk.Sdk(windfarmer_installation_folder)
print(' > SDK is now up and running!')

#%% Define folders for inputs and results - using relative paths in this repository
import os
script_dir_name = os.path.dirname(__file__) # Note it is better not to use os.path.curdir as it changes depending on whether running as a notebook or python script 
root_dir = os.path.abspath(os.path.join(script_dir_name, '..', '..', '..'))
workbook_folder_path = os.path.join(root_dir, 'DemoData', 'OffshoreBalticCoast')
results_directory = os.path.join(script_dir_name, 'AEPInputsJson')

#%% extract energy calculation inputs for every scenario in every WFA workbook
success = True
print( "Starting process to export WindFarmer AEP web API input json")
for filename in os.listdir(workbook_folder_path):
    if filename.endswith(".wwx") or filename.endswith(".wow"): 
        # Open WindFarmer workbook
        print( "> opening windfarmer workbook..." + filename )
        wf.Toolbox.OpenWorkbook(os.path.join(workbook_folder_path, filename))
        
        project_name = os.path.basename(wf.Toolbox.get_CurrentWorkbookPath())
        print("> WindFarmer workbook opened: " + project_name)
        
        for layout_scenario in wf.Workbook.LayoutScenarios:
            try:
                wf.Toolbox.ActivateLayoutScenario(layout_scenario)
                print (f'>\t Activated scenario {layout_scenario.Name}')
                
                # export inputs for an API calc
                json_export_file_name = f'{os.path.splitext(project_name)[0]}_{layout_scenario.Name}.json'
                json_path = os.path.join(results_directory, json_export_file_name)
                wf.Toolbox.ExportWindFarmerEnergyJson(json_path)
                print (">\t exported AEP web API inputs to: " + json_path + "\n")

            except Exception as e:
                print(str(e))
                success = False

wf.Toolbox.NewWorkbook()

if (success):
    print("SUCCESS")
else:
    print("FAIL")
