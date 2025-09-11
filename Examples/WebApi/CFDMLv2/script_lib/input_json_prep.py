"""
Self-contained utilities for preparing input JSON for CFD.ML calculations.

This module contains functions to help setup inputs specific to running CFD.ML
via the WindFarmer API, including model settings, atmospheric conditions, 
and various calculation configurations.
"""

import numpy as np

# Large wind farm correction parameters (default offshore settings)
lwf_paramters = {
    "baseRoughnessZ01": 0.0004,
    "increasedRoughnessZ02": 0.0192,
    "geometricWidthDiameters": 1.0,
    "recoveryStartDiameters": 120.0,
    "fiftyPercentRecoveryDiameters": 40.0
}


def get_wake_models(cfdml_version="2.6.0"):
    """
    Get wake model configurations.
    
    Parameters:
    -----------
    cfdml_version : str, optional
        Version of CFDML to use (default: "2.6.0")
        
    Returns:
    --------
    dict
        Dictionary of wake model configurations
    """
    return {
        "EddyViscosity": {
            "model_key": "eddyViscosity", 
            "model_settings": {
                "useLargeWindFarmModel": True, 
                "largeWindFarmCorrectionParameters": lwf_paramters
            }
        },
        "ModifiedPark": {
            "model_key": "modifiedPark", 
            "model_settings": {
                "useLargeWindFarmModel": True, 
                "largeWindFarmCorrectionParameters": lwf_paramters
            }
        },
        "TurbOPark": {
            "model_key": "turbOPark", 
            "model_settings": {
                "wakeExpansion": 0.04
            }
        },
        "CFDML": {
            "model_key": "cfdml", 
            "model_settings": {
                "gnnType": "Offshore", 
                "gnnVersion": cfdml_version, 
                "extrapolationModel": "EddyViscosity"
            }
        }
    }


def get_blockage_models(cfdml_version="2.6.0", blockage_application_method="OnWindSpeed"):
    """
    Get blockage model configurations.
    
    Parameters:
    -----------
    cfdml_version : str, optional
        Version of CFDML to use (default: "2.6.0")
    blockage_application_method : str, optional
        Method for applying blockage correction (default: "OnWindSpeed")
        
    Returns:
    --------
    dict
        Dictionary of blockage model configurations
    """
    return {
        "BEET": {
            "model_key": "beet", 
            "model_settings": {
                "significantAtmosphericStability": False,
                "inclusionOfNeighborsBufferZoneInMeters": 1000.0,
                "blockageCorrectionApplicationMethod": blockage_application_method
            }
        },
        "CFDML": {
            "model_key": "cfdml", 
            "model_settings": {
                "cfdmlSettings": {
                    "gnnType": "Offshore", 
                    "gnnVersion": cfdml_version
                }, 
                "blockageCorrectionApplicationMethod": blockage_application_method,
                "cfdmlBlockageWindSpeedDependency": "FromBlockageExtrapolationCurve"
            }
        }
    }


def switch_off_fpm_export(input_json):
    """
    Switch off FPM (Flow and Performance Matrix) export to speed up API response time.
    
    Parameters:
    -----------
    input_json : dict
        The input JSON configuration dictionary
    """
    # this function makes sure fpm export is switched off - to speed up API response time
    for fpm in input_json["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"].keys():
        if fpm != "localTurbineWindSpeedsOutputSettings":
            input_json["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"][fpm] = False
        else:
            input_json["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"][fpm] = None


def configure_fpm_export(input_json):
    """
    Configure FPM export settings to output wind speed data.
    
    Parameters:
    -----------
    input_json : dict
        The input JSON configuration dictionary
    """
    input_json["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"]["outputAmbientWindSpeed"] = True
    input_json["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"]["outputWakedWindSpeed"] = True
    #input_json["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"]["outputPowerOutput"] = True


def set_model_settings(input_json, wake_model_choice, blockage_model_choice, 
                      calculate_efficiencies, number_of_direction_steps,
                      cfdml_version="2.6.0", blockage_application_method="OnWindSpeed"):
    """
    Set model settings for wake and blockage calculations.
    
    Parameters:
    -----------
    input_json : dict
        The input JSON configuration dictionary
    wake_model_choice : str
        Wake model to use (EddyViscosity/ModifiedPark/TurbOPark/CFDML)
    blockage_model_choice : str
        Blockage model to use (BEET/CFDML)
    calculate_efficiencies : bool
        Whether to calculate efficiencies
    number_of_direction_steps : int
        Number of direction steps for wake calculation
    cfdml_version : str, optional
        Version of CFDML to use (default: "2.6.0")
    blockage_application_method : str, optional
        Method for applying blockage correction (default: "OnWindSpeed")
    """
    # Get model configurations with current parameters
    wake_models = get_wake_models(cfdml_version)
    blockage_models = get_blockage_models(cfdml_version, blockage_application_method)
    
    # let's set the modeling options contained in the json
    input_json["energyEfficienciesSettings"]["calculateEfficiencies"] = calculate_efficiencies
    input_json["energyEfficienciesSettings"]["includeHysteresisEffect"] = False
    input_json["energyEfficienciesSettings"]["includeTurbineManagement"] = False
    input_json["energyEfficienciesSettings"]["calculateIdealYield"] = False

    input_json['energyEfficienciesSettings']['numberOfDirectionSectorsForWakeCalculation'] = number_of_direction_steps
    
    # pull the relevant default settings from the dicts predefined above
    input_json["energyEfficienciesSettings"]["wakeModel"]["wakeModelType"] = wake_model_choice
    input_json["energyEfficienciesSettings"]["wakeModel"][wake_models[wake_model_choice]["model_key"]] = wake_models[wake_model_choice]["model_settings"]
    
    if wake_model_choice == "CFDML":
        extrapolation_model = wake_models["CFDML"]["model_settings"]["extrapolationModel"]
        if extrapolation_model != "BasicFlat":
            input_json["energyEfficienciesSettings"]["wakeModel"][wake_models[extrapolation_model]["model_key"]] = wake_models[extrapolation_model]["model_settings"]
    
    input_json["energyEfficienciesSettings"]["blockageModel"]["blockageModelType"] = blockage_model_choice
    input_json["energyEfficienciesSettings"]["blockageModel"][blockage_models[blockage_model_choice]["model_key"]] = blockage_models[blockage_model_choice]["model_settings"]


def get_avg_hub_and_tip_heights_for_subject_windfarms(input_json):
    """
    Calculate average hub and tip heights for non-neighbor wind farms.
    
    Parameters:
    -----------
    input_json : dict
        The input JSON configuration dictionary
        
    Returns:
    --------
    tuple
        (avg_hub_heights, avg_tip_heights) in meters
    """
    hub_heights = []
    tip_heights = []
    turbine_model_heights = {}
    
    for turbine_model in input_json["turbineModels"]:
        turbine_model_heights[turbine_model["id"]] = {
            "hub_height": turbine_model["hubHeight_m"],
            "tip_height": turbine_model["hubHeight_m"] + turbine_model["rotorDiameter_m"] / 2.0,
        }

    for subject_wind_farm in input_json["windFarms"]: 
        if subject_wind_farm["isNeighbor"] == False:
            for turbine in subject_wind_farm["turbines"]:
                turbine_id = turbine["turbineModelId"]
                hub_heights.append(turbine_model_heights[turbine_id]["hub_height"])
                tip_heights.append(turbine_model_heights[turbine_id]["tip_height"])
                
    avg_tip_heights = np.average(tip_heights)
    avg_hub_heights = np.average(hub_heights)
    return avg_hub_heights, avg_tip_heights


def interpolate_profile_at_height(z, zs, profile_values):
    """
    Interpolate profile values at a specific height using linear interpolation.
    
    Parameters:
    -----------
    z : float
        Height at which to interpolate
    zs : list
        Height levels
    profile_values : list
        Profile values at corresponding heights
        
    Returns:
    --------
    float
        Interpolated value at height z
    """
    ## we may want something better than linear interpolation?
    # cubicspline_interpolator = scipy.interpolate.CubicSpline(zs, profile_values)
    # value_at_z = cubicspline_interpolator(standard_zs)
    value_at_z = np.interp(z, zs, profile_values)
    return value_at_z


def construct_atmospheric_conditions(atmospheric_condition_probability_distribution, 
                                    atmospheric_condition_presets, hub_height, tip_height):
    """
    Construct atmospheric conditions object from presets and probability distribution.
    
    Parameters:
    -----------
    atmospheric_condition_probability_distribution : list
        List of dictionaries defining probability distribution by direction
    atmospheric_condition_presets : dict
        Dictionary of atmospheric condition presets
    hub_height : float
        Hub height in meters
    tip_height : float
        Tip height in meters
        
    Returns:
    --------
    dict
        Complete atmospheric conditions configuration
    """
    # constructing the whole atmospheric conditions object
    selected_preset_classes = []
    for bin_data in atmospheric_condition_probability_distribution:
        selected_preset_classes.extend(bin_data["atmosphericConditionClassIds"])
    selected_preset_classes = list(set(selected_preset_classes))
    
    atmospheric_condition_classes = []
    for preset in selected_preset_classes:
        atmospheric_condition_class = {} 
        atmospheric_condition_class["id"] = preset
        
        parameters = {}
        # read tip and hub height data from profiles
        zs = atmospheric_condition_presets[preset]["z"]
        dvdzs = atmospheric_condition_presets[preset]["dvdz"]
        tis = atmospheric_condition_presets[preset]["ti"]
        
        parameters["turbulenceIntensityAtHubHeight"] = interpolate_profile_at_height(hub_height, zs, tis)
        parameters["turbulenceIntensityAtTipHeight"] = interpolate_profile_at_height(tip_height, zs, tis)
        parameters["windSpeedVerticalGradientHubHeight_per_m"] = interpolate_profile_at_height(hub_height, zs, dvdzs)
        parameters["windSpeedVerticalGradientTipHeight_per_m"] = interpolate_profile_at_height(tip_height, zs, dvdzs)
        parameters["boundaryLayerHeight_m"] = atmospheric_condition_presets[preset]["boundaryLayerHeight_m"]
        parameters["lapseRate_K_per_100m"] = atmospheric_condition_presets[preset]["lapseRate_K_per_100m"]
        parameters["deltaThetaAcrossInversionLayer_K"] = atmospheric_condition_presets[preset]["deltaThetaAcrossInversionLayer_K"]
        parameters["heightInversionLayer_m"] = atmospheric_condition_presets[preset]["heightInversionLayer_m"]

        atmospheric_condition_class["parameters"] = parameters
        atmospheric_condition_classes.append(atmospheric_condition_class)

    atmospheric_conditions = {
        "atmosphericConditionClasses": atmospheric_condition_classes,
        "atmosphericConditionProbabilityDistribution": atmospheric_condition_probability_distribution
    }
    return atmospheric_conditions


def set_model_settings_for_blockage_only_runs(input_json):
    """
    Configure settings for blockage-only calculations (no wake effects).
    
    Parameters:
    -----------
    input_json : dict
        The input JSON configuration dictionary
    """
    # turn off wake models etc. so only considering blockage for speed of computation of AEP calculation
    input_json['energyEfficienciesSettings']['wakeModel']['wakeModelType'] = 'NoWakeModel'
    input_json["energyEfficienciesSettings"]["wakeModel"]["noWakeModel"]["useLargeWindFarmModel"] = False
    input_json["energyEfficienciesSettings"]["calculateEfficiencies"] = False
    input_json["energyEfficienciesSettings"]["includeHysteresisEffect"] = False
    input_json["energyEfficienciesSettings"]["includeTurbineManagement"] = False
    input_json["energyEfficienciesSettings"]["calculateIdealYield"] = False
    switch_off_fpm_export(input_json)