#  Script to compute Full AEP for every scenario and workbook from a folder of WFA workbooks

#%% Setup connection to the WFA SDK
import windfarmer.sdk
windfarmer_installation_folder = r'C:\Program Files\DNV\WindFarmer - Analyst 1.3.6.2'
wf = windfarmer.sdk.Sdk(windfarmer_installation_folder)
print(' > SDK is now up and running!')

#%% Define folders for inputs and results - using relative paths in this repository
import os
script_dir_name = os.path.dirname(__file__) # Note it is better not to use os.path.curdir as it changes depending on whether running as a notebook or python script 
root_dir = os.path.abspath(os.path.join(script_dir_name, '..', '..', '..'))
workbook_folder_path = os.path.join(root_dir, 'DemoData', 'OffshoreBalticCoast')


#%% Open workbooks and calculate energy
result_string = "Results: \n"
success = True

# Open each WindFarmer workbook in turn within the given folder
for filename in os.listdir(workbook_folder_path):
    if filename.endswith(".wwx") or filename.endswith(".wow"): 
        print( "opening windfarmer workbook..." + filename )
        wf.Toolbox.OpenWorkbook(os.path.join(workbook_folder_path, filename))
        
        print("> WindFarmer file opened: " + wf.Toolbox.get_CurrentWorkbookPath() + "\n")

        for layout_scenario in wf.Workbook.LayoutScenarios:
            try:
                wf.Toolbox.ActivateLayoutScenario(layout_scenario)
                print (f'> Activated scenario {layout_scenario.Name}')
                
                # Set some energy calculation settings
                energySettings = wf.Workbook.ModelSettings.EnergySettings
                energySettings.WakeModelType =  wf.Scripting.WakeModelType.EddyViscosity
                energySettings.ApplyLargeWindFarmCorrection = True
                energySettings.CalculationToUse = wf.Scripting.EnergyCalculationToUseType.New
                energySettings.CalculateEfficiencies = False
                energySettings.LargeWindFarmCorrectionSettings.BaseRoughness = 0.0002
                energySettings.LargeWindFarmCorrectionSettings.IncreasedRoughness = 0.0192
                energySettings.LargeWindFarmCorrectionSettings.DistanceInDiametersToStartOfRecovery = 120
                energySettings.NumberOfDirectionSectors = 180
                
                # Compute the full yield
                print (f'Computing energy for layout scenario {layout_scenario.Name}')
                results_scenario = wf.Toolbox.CalculateEnergy()
                print ('Finished energy calculation!')
                
                # Read some results
                subjectWindFarm = [x for x in results_scenario.WindFarms if x.IsNeighbour == False][0]
                full_yeild = results_scenario.FarmTotalYields.GetVariantResult("Full").GetValueForFarm(subjectWindFarm).Value / 10e6	
                result = str.format("Full yield for scenario {0}:\t{1:.2f} GWh/annum\n", layout_scenario.Name, full_yeild)
                result_string += result
                print (result )

            except Exception as e:
                print(str(e))
                success = False

# Closes the open workbook:
wf.Toolbox.NewWorkbook()

if (success):
    print("SUCCESS")
    print(result_string)
else:
    print("FAIL")
