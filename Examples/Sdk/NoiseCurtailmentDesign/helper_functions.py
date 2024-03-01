def set_noise_limit_all_receptors(wfWorkbook, noise_limit):
    print("Setting all receptors noise limit to {} dB".format(noise_limit))
    for r in wfWorkbook.Receptors:
        r.AbsoluteNoiseLimit = noise_limit

def get_list_turbines(wfWorkbook):
    turbs = []
    for f in wfWorkbook.WindFarms:
        if f.IsNeighbour == False:
            for t in f.Turbines:
                turbs.append(t.Name)
    return turbs

def get_list_as_dict(list):
    list_as_dict = dict()
    for i in range(len(list)):
        list_as_dict[list[i]] = i
        
    return list_as_dict

def set_mode_on_turbine_type(wfWorkbook, mode_name, turbine_type_name):
    if mode_name == "Normal":
        mode_name = "Normal mode"
    mode = next(iter([x for x in wfWorkbook.TurbineTypes[turbine_type_name].TurbineModes if x.Name == mode_name]))
    mode.SetNormalMode()

def index3D(i, j, k, nx, ny):
    return i + nx*j + (nx*ny)*k

def index2D(i, j, nx):
    return i + nx*j

def parse_noise_results_and_store(wfWorkbook, receptors, receptors_as_dict, turbines_as_dict, mode_idx, n_modes, n_turbines, noise_per_mode_from_turbine_for_receptors):
    for result in wfWorkbook.CurrentScenario.Noise.Results.ReceptorResults:
        if result.Name not in receptors:
            continue
                        
        receptor_idx = receptors_as_dict[result.Name]								
        
        # Loop through noise 
        for turb_contrib in result.TurbineSourceContibutions:
            if turb_contrib.Name not in turbines_as_dict:
                continue # neighbours
            turbine_idx = turbines_as_dict[turb_contrib.Name]	
            # Store result as Sound pressure				
            sp = pow(10.0, 0.1* turb_contrib.NoiseContribution)            
            noise_per_mode_from_turbine_for_receptors[index3D(mode_idx, turbine_idx, receptor_idx, n_modes, n_turbines)] = sp

def run_energy_calculation(wfWorkbook, wfToolbox):
    wfWorkbook.ModelSettings.EnergySettings.CalculateEfficiencies = False
    wfWorkbook.ModelSettings.EnergySettings.ApplyWakeModel = False
    wfWorkbook.ModelSettings.EnergySettings.ApplyCurtailmentRules = False
    wfWorkbook.ModelSettings.EnergySettings.CalculateBlockageEfficiency = False
    wfWorkbook.ModelSettings.EnergySettings.CalculateIdealYield = False			
    wfWorkbook.ModelSettings.EnergySettings.UseAssociationMethod = False
    scenario = wfToolbox.CalculateEnergy()
    return scenario

def parse_energy_results_and_store(scenario, turbines, turbines_as_dict, mode_idx, n_modes, gross_per_mode_per_turbine):
    for rot in iter([t for t in scenario.Turbines if t.Name in turbines]):
        gross = scenario.TurbineTotalYields.GetVariantResult("Gross").GetValueForTurbine(rot).Value
        turbine_idx = turbines_as_dict[rot.Name]
        gross_per_mode_per_turbine[index2D(mode_idx, turbine_idx, n_modes)] = gross/1e6

def check_strategy_for_all_receptors(strategy, receptors, receptors_as_dict, n_turbines, modes_as_dict, n_modes, noise_per_mode_from_turbine_for_receptors, noise_limit):
    import math
    does_noise_exceed = False
    for recept in receptors:
        receptor_idx = receptors_as_dict[recept]
        sum = 0.0
        
        # calculate the noise from combination
        for turbine_idx in range(n_turbines):
            mode = strategy[turbine_idx]
            mode_idx = modes_as_dict[mode]
            sum += noise_per_mode_from_turbine_for_receptors[index3D(mode_idx, turbine_idx, receptor_idx, n_modes, n_turbines)]
        try:
            total_noise = 10.0*math.log10(sum)
        except:
            print("sum noise {}, receptor {}".format(sum, recept))
            total_noise = noise_limit+1
        is_noise_exceeded = (total_noise > noise_limit)
        
        if is_noise_exceeded:
            does_noise_exceed = True
            break
    
    return does_noise_exceed
    
def get_gross_for_strategy(strategy, n_turbines, modes_as_dict, n_modes, gross_per_mode_per_turbine):
    gross_sum = 0.0
    for turbine_idx in range(n_turbines):
        mode = strategy[turbine_idx]
        mode_idx = modes_as_dict[mode]
        gross_sum += gross_per_mode_per_turbine[index2D(mode_idx, turbine_idx, n_modes)]
    return gross_sum