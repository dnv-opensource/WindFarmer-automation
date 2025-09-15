import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from copy import deepcopy

def read_stable_weights(stable_weights_file_path):
    stable_weights_df = pd.read_csv(stable_weights_file_path, sep='\t', engine='python', index_col=[0])
    stable_weights_df.index.name = "bin_centre"
    stable_weights_df.columns = ["stable_weight"]
    number_of_equal_sectors = stable_weights_df.shape[0] # assumes stable weight bins are equally spaced.
    bin_width = 360 / number_of_equal_sectors
    
    stable_weights_df["fromDirection_degrees"] = stable_weights_df.index.map(lambda x: (x - bin_width/2) % 360)
    stable_weights_df["toDirection_degrees"] = stable_weights_df.index.map(lambda x: (x + bin_width/2) % 360)
    return stable_weights_df

def parse_stable_weights_to_atmos_condition_prob_dist(stable_weights_file_path, stable_atmos_condition_class_name, unstable_atmos_condition_class_name, single_preset_condition = None):
    if single_preset_condition:
        single_atmos_condition ={}
        single_atmos_condition["fromDirection_degrees"] = 0.0
        single_atmos_condition["toDirection_degrees"] = 360.0
        single_atmos_condition["probabilityForClasses"] = [1.0]
        single_atmos_condition["atmosphericConditionClassIds"] = [single_preset_condition]
        atmos_prob_dist_dict = [single_atmos_condition]
        return atmos_prob_dist_dict
    
    if stable_weights_file_path is not None:
        stable_weights_df = read_stable_weights(stable_weights_file_path)
    else:
        raise ValueError(f"attempting to set up atmos condtion probability dict with multiple classes but no stable weights file available!")
    stable_weights_df["probabilityForClasses"] = stable_weights_df["stable_weight"].map(lambda x: [x, 1-x])
    stable_weights_df["atmosphericConditionClassIds"] = stable_weights_df.index.map(lambda x: [stable_atmos_condition_class_name, unstable_atmos_condition_class_name])
    stable_weights_df = stable_weights_df.drop("stable_weight", axis=1)
    atmos_condition_prob_dist = [sector for sector in stable_weights_df.T.to_dict().values()]
    return atmos_condition_prob_dist

def get_avg_hub_and_tip_heights_for_subject_windfarms(input_json):
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
                id = turbine["turbineModelId"]
                hub_heights.append(turbine_model_heights[id]["hub_height"])
                tip_heights.append(turbine_model_heights[id]["tip_height"])
    avg_tip_heights = np.average(tip_heights)
    avg_hub_heights = np.average(hub_heights)
    return avg_hub_heights, avg_tip_heights

def interpolate_profile_at_height( z, zs, profile_values):
    ## we may want something better than linear interpolation?
    # cubicspline_interpolator = scipy.interpolate.CubicSpline(zs, profile_values)
    # value_at_z = cubicspline_interpolator(standard_zs)
    value_at_z = np.interp(z, zs, profile_values)
    return value_at_z

def construct_atmospheric_conditions(atmosphericConditionProbabilityDistribution, atmosperhic_condition_presets, hub_height, tip_height):
    # constructing the whole atmospheric conditions object
    selected_preset_classes = []
    for bin in atmosphericConditionProbabilityDistribution:
        selected_preset_classes.extend(bin["atmosphericConditionClassIds"])
    selected_preset_classes = list(set(selected_preset_classes))
    
    atmosphericConditionClasses = []
    for preset in selected_preset_classes:
        atmosphericConditionClass = {} 
        atmosphericConditionClass["id"] = preset
        
        parameters = {}
        # read tip and hub height data from profiles
        zs = atmosperhic_condition_presets[preset]["z"]
        dvdzs = atmosperhic_condition_presets[preset]["dvdz"]
        tis = atmosperhic_condition_presets[preset]["ti"]
        parameters["turbulenceIntensityAtHubHeight"] = interpolate_profile_at_height(hub_height, zs, tis)
        parameters["turbulenceIntensityAtTipHeight"] = interpolate_profile_at_height(tip_height, zs, tis)
        parameters["windSpeedVerticalGradientHubHeight_per_m"] = interpolate_profile_at_height(hub_height, zs, dvdzs)
        parameters["windSpeedVerticalGradientTipHeight_per_m"] = interpolate_profile_at_height(tip_height, zs, dvdzs)
        parameters["boundaryLayerHeight_m"] = atmosperhic_condition_presets[preset]["boundaryLayerHeight_m"]
        parameters["lapseRate_K_per_100m"] = atmosperhic_condition_presets[preset]["lapseRate_K_per_100m"]
        parameters["deltaThetaAcrossInversionLayer_K"] = atmosperhic_condition_presets[preset]["deltaThetaAcrossInversionLayer_K"]
        parameters["heightInversionLayer_m"] = atmosperhic_condition_presets[preset]["heightInversionLayer_m"]

        atmosphericConditionClass["parameters"] = parameters
        atmosphericConditionClasses.append(atmosphericConditionClass)

    atmosphericConditions = {
        "atmosphericConditionClasses": atmosphericConditionClasses,
        "atmosphericConditionProbabilityDistribution": atmosphericConditionProbabilityDistribution
    }
    return atmosphericConditions

def plot_atmoshperic_conditions_rose(atmosphericConditionProbabilityDistribution):
    """ 
    Plot the atmospheric conditions class rose to visualise the directional frequency of atmospheric stability.
    """
    # Plot the frequency distribution of atmospheric conditions
    all_atmos_classes = []
    for sector in atmosphericConditionProbabilityDistribution:
        for class_id in sector["atmosphericConditionClassIds"]:
            if class_id not in all_atmos_classes:
                all_atmos_classes.append(class_id)
    print(f'Distinct atmospheric conditions classes to simulate:\n {all_atmos_classes}')

    temp = pd.DataFrame(atmosphericConditionProbabilityDistribution)
    df_for_stability_rose_plot = pd.DataFrame()
    for i in range(0,2):
        temp2 = temp.copy()
        temp2['atmosphericConditionClassIds'] = temp2['atmosphericConditionClassIds'].apply(lambda x: x[i])
        temp2['probabilityForClasses'] = temp2['probabilityForClasses'].apply(lambda x: x[i])
        df_for_stability_rose_plot = pd.concat([df_for_stability_rose_plot, temp2], axis=0)
    df_for_stability_rose_plot['angular_bin_center'] = pd.Series([_average_angles([math.radians(x["toDirection_degrees"]), math.radians(x["fromDirection_degrees"])]) for x in atmosphericConditionProbabilityDistribution])#  pd.Series([50, 200, 315, 40, 130, 315])
    df_for_stability_rose_plot['angular_bin_center_degrees'] = df_for_stability_rose_plot['angular_bin_center'].map(lambda x: math.degrees(x))
    df_for_stability_rose_plot['angular_bin_width'] = pd.Series([_angle_difference(math.radians(x["toDirection_degrees"]),math.radians(x["fromDirection_degrees"])) for x in atmosphericConditionProbabilityDistribution])#  pd.Series([50, 200, 315, 40, 130, 315])
    df_for_stability_rose_plot['angular_bin_width_degrees'] = df_for_stability_rose_plot['angular_bin_width'].map(lambda x: math.degrees(x))
    df_for_stability_rose_plot['cumulative_probability'] = df_for_stability_rose_plot.groupby('angular_bin_center')['probabilityForClasses'].cumsum()

    df_for_stability_rose_plot

    fig, ax = plt.subplots(subplot_kw={'projection':'polar','theta_offset': np.pi / 2, 'theta_direction': -1})
    for key in all_atmos_classes:
        group = df_for_stability_rose_plot[df_for_stability_rose_plot['atmosphericConditionClassIds']==key]
        ax.bar(group['angular_bin_center'], group['probabilityForClasses'], bottom=group['cumulative_probability']-group['probabilityForClasses'],  width=group['angular_bin_width'], label=f'Class {key}', edgecolor='black')
    ax.set_ylim([-0.2, 1.0])
    fig.suptitle("Frequency of atmospheric conditions by wind direction")
    fig.legend(loc='lower center')

def check_if_neighbours(input_aep_json):
    neighbour_farms = [w for w in input_aep_json["windFarms"] if w["isNeighbor"]==True]
    return len(neighbour_farms) > 0

def generate_no_neighbours_inputs(input_aep_json_with_neighbours):
    if check_if_neighbours(input_aep_json_with_neighbours):
        aep_inputs_no_neighbours = deepcopy(input_aep_json_with_neighbours)
        aep_inputs_no_neighbours["windFarms"] = [w for w in input_aep_json_with_neighbours["windFarms"] if w["isNeighbor"]==False]
    else:
        aep_inputs_no_neighbours = input_aep_json_with_neighbours
    return aep_inputs_no_neighbours

def _average_angles(angles_in_radians):
    #Calculate the sum of sine and cosine components
    sin_sum = sum(math.sin(angle) for angle in angles_in_radians)
    cos_sum = sum(math.cos(angle) for angle in angles_in_radians)
    
    # Calculate the average angle in radians
    result = math.atan2(sin_sum, cos_sum)
    # ensure within 0-2pi
    if result < 0:
        result = 2*math.pi +result
    elif result > 2*math.pi:
        result = result - 2*math.pi
    return result

def _angle_difference(to_angle_in_radians, from_angle_in_radians):
    if to_angle_in_radians < from_angle_in_radians:
        from_angle_in_radians = from_angle_in_radians - 2*math.pi
    angle_difference = to_angle_in_radians - from_angle_in_radians
    return  angle_difference 