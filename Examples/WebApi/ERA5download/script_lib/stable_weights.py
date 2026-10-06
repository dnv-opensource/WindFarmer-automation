import os
import re
import pandas as pd
from .era5_signal_download_and_processing import load_era5_data_from_file

def get_stability_weights_from_era5(project_name, use_cached_derived_signals, era5_cache_directory, n_direction_bins):
    """
    Get the stability weights for the given project from ERA5 data. The raw data need to be downloaded first using the function download_era5_data_for_site.
    
    Parameters:
    project_name (str): The name of the project.
    use_cached_derived_signals (bool): Whether to use the cached derived signals from the ERA5 data. This refers to the stability metrics derivation. 
    era5_cache_directory (str): The directory where the ERA5 data is cached.

    Returns:
    A tuple of pd.DataFrame containing the stability weights for the stability derivation methods in the columns.
    """
    
    if not os.path.exists(os.path.join(era5_cache_directory, f"era5_{project_name}.csv")):
        raise Exception("No ERA5 data found for project {}. Please download the data first.".format(project_name))
    df = load_era5_data_from_file(project_name, use_cached_derived_signals, era5_cache_directory)
    
    era5_weights_results = {}
    if 'classification_hf' in df.columns:
        era5_hf_weights = derive_sectorwise_stable_weights(df, True, 'hf', n_direction_bins)
        era5_weights_results["hf"] = era5_hf_weights
        
    if 'classification_mol' in df.columns:
        era5_mol_weights = derive_sectorwise_stable_weights(df, True, 'mol', n_direction_bins)
        era5_weights_results["mol"] = era5_mol_weights
    
    if 'classification_mol'  in df.columns and 'classification_hf' in df.columns:
        era5_blend_weights = (era5_mol_weights + era5_hf_weights) / 2
        era5_weights_results["blend"] = era5_blend_weights

    results = pd.DataFrame(era5_weights_results)
    # ToDo - accept different numbers of direction sectors
    return results

def _find_matching_era5_processed_signal(project_name, era5_cache_directory):
    project_identifier = project_name.split(" ")[0] # we want the first word of the project name as it is common for the possible variants of a given project
    matching_files = [f for f in os.listdir(os.path.join("./", era5_cache_directory)) if re.match(f"^era5_{project_identifier}.*_processed.csv", f)]
    if len(matching_files) != 1:
        return None
    return matching_files[0].replace("era5_","").replace("_processed.csv","") # the corresponding project name

def prepare_era5_stable_weights_for_api_baseline_inputs(project_name, results_folder, era5_cache_directory, era5_method, overwrite, n_direction_bins = 12):
    """
    Creates a stable weights file for the project in the results folder using the requested method
    Parameters
    ----------
    project_name : string, used to name the file

    results_folder: root folder for stable weights. A folder is created within this for each project

    era5_method : 'blend', 'hf'
        The method to derive the stability weights. Options: 'blend', 'hf'.
    
    overwrite : whether to reprocess the raw downloaded data or not
    
    """
    def _prepare_stable_weights_for_project(n_direction_bins):
        sister_project_with_era5_data_available = _find_matching_era5_processed_signal(project_name, era5_cache_directory) # make sure to reserve a unique first word for projects which are in different locations
        if sister_project_with_era5_data_available is not None:
            weights = get_stability_weights_from_era5(sister_project_with_era5_data_available, use_cached_derived_signals=False, era5_cache_directory=era5_cache_directory, n_direction_bins= n_direction_bins) # will error if the data wasn't downloaded beforehand
        else:
            #try processing the data based on raw era5 downloads, if present
            try:
                load_era5_data_from_file(project_name, False, era5_cache_directory) # this should process the raw data and save a *_processed.csv file
            except:
                print(f"No matching ERA5 data found for project {project_name}, skipping. Please download the data first.")
                return
            weights = get_stability_weights_from_era5(project_name, use_cached_derived_signals=True, era5_cache_directory=era5_cache_directory, n_direction_bins= n_direction_bins)
        destination_era5_stable_weights_file_path = os.path.join(results_folder, project_name, "era5_stable_weights.txt")
        weights = weights.loc[:,era5_method].to_frame()
        weights.index.name = "bin_centre"
        if len(weights.columns)  == 0:
            raise Exception("Multiple columns found in the ERA5 stable weights data. Please check the data.")
        weights.columns = ["stable_weight"]
        os.makedirs(os.path.dirname(destination_era5_stable_weights_file_path), exist_ok=True)
        weights.to_csv(destination_era5_stable_weights_file_path, sep='\t')
        print(f"ERA5 stable weights for project {project_name} written to {destination_era5_stable_weights_file_path}")
        
    destination_era5_stable_weights_file_path = os.path.join(results_folder, project_name, "era5_stable_weights.txt")
    if not os.path.exists(destination_era5_stable_weights_file_path):
        _prepare_stable_weights_for_project(n_direction_bins)
    elif overwrite:
        _prepare_stable_weights_for_project(n_direction_bins)
    else:
        print(f"{destination_era5_stable_weights_file_path} already exists, skipping")
    return destination_era5_stable_weights_file_path

def read_stable_weights(stable_weights_file_path):
    """
    Read the stable weights from file
    Parameters
    ----------
    stable_weights_file_path : path of the stable weights tab separated text tile
    Returns
    -------
    weights : a pandas.DataFrame
        The sector-wise stability weights for the site with useful binning information required to use the weights in the WindFarmer API 
    """
    stable_weights_df = pd.read_csv(stable_weights_file_path, sep='\t', engine='python', index_col=[0])
    stable_weights_df.index.name = "bin_centre"
    stable_weights_df.columns = ["stable_weight"]
    number_of_equal_sectors = stable_weights_df.shape[0] # assumes stable weight bins are equally spaced.
    bin_width = 360 / number_of_equal_sectors
    
    stable_weights_df["fromDirection_degrees"] = stable_weights_df.index.map(lambda x: (x - bin_width/2) % 360)
    stable_weights_df["toDirection_degrees"] = stable_weights_df.index.map(lambda x: (x + bin_width/2) % 360)
    return stable_weights_df

def derive_sectorwise_stable_weights(subset_df, consider_neutral_as_unstable=True, stab_method='mol', n_direction_bins = 12):
    """
    Derive the stability weights.
    Parameters
    ----------
    subset_df : a pandas.DataFrame
        The subset of the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span, with appended stability metrics.
    weighting_method : a string
        The method to derive the stability weights. Options: 'new', 'old'.  
    stab_method : a string
        The method used to derive the stability classes. Options: 'mol', 'ri10'.
    
    Returns
    -------
    weights : a pandas.DataFrame
        The sector-wise stability weights for the site.
    """
    subset_df[r'classification_{}_simple'.format(stab_method)] = \
        subset_df[r'classification_{}'.format(stab_method)].apply(lambda x: simplify_stability_classes(x, stab_method, consider_neutral_as_unstable))

    bin_width = 360 / n_direction_bins
    first_bin_upper_bound = bin_width / 2.0
    # Bin the wind direction into 30 degree bins, with the first bin spanning 354-15 degrees
    bin_uppers = [x * bin_width + first_bin_upper_bound for x in range(0, n_direction_bins)]
    def which_bin(dir_in_degs):
        no_right_bin_boundaries_smaller_than_dir = sum([dir_in_degs <= x  for x in bin_uppers])
        return n_direction_bins-no_right_bin_boundaries_smaller_than_dir + 1 if no_right_bin_boundaries_smaller_than_dir != 0 else 1
    
    subset_df['dir_bin'] = subset_df['wind_dir'].apply(which_bin)

    #split at the inflection points, no neutral category
    sectorwise_count = subset_df.groupby(['dir_bin',r'classification_{}_simple'.format(stab_method)], observed=True).count()['wind_dir']
    # sometimes it happends that bins are empty, we want to ensure that all bins are present in the output even if empty
    level0 = list(range(1, n_direction_bins+1, 1))
    level1 = ['stable', 'not-stable']
    sectorwise_count = sectorwise_count.reindex(pd.MultiIndex.from_product([level0, level1], names=['dir_bin', 'classification_{}_simple'.format(stab_method)]), fill_value=0)
    for sector in sectorwise_count.index.levels[0]:
        if 'stable' in sectorwise_count.loc[sector,:].index and sectorwise_count.loc[sector,['stable','not-stable']].sum() != 0:
            sectorwise_count.loc[sector, 'stable_weight'] = sectorwise_count.loc[sector,'stable'] / sectorwise_count.loc[sector,['stable','not-stable']].sum() #not counting records for which stability lassification yielded "unknown"
        else:
            sectorwise_count.loc[sector, 'stable_weight'] = 0
    
    sectorwise_count.sort_index(inplace=True)
    # extracting only the stable weights
    stable_weights = sectorwise_count[:,'stable_weight']
        # converting index to bin center in degrees
    stable_weights.index = ((stable_weights.index - 1) * bin_width) 
    
    return stable_weights

def simplify_stability_classes(stab_class, stab_method, consider_neutral_as_not_stable):
    """
    Simplify the stability classes to stable/unstable.

    Parameters
    ----------
    stab_class : a string
        The stability classification string to be simplified.
    stab_method : a string
        The method used to derive the stability classes. Options: 'mol', 'ri10'.
    consider_neutral_as_unstable : a boolean
        Whether to consider the neutral class as unstable.

    Returns
    -------
    simplified : a string
        The simplified stability class.
    """
    simplify_mol = {
        'neutral-': 'not-stable',
        'near-neutral-u': 'not-stable',
        'unstable': 'not-stable',
        'very-unstable': 'not-stable',
        'very-unstable?': 'not-stable',
        'very-stable': 'stable',
        'stable': 'stable',
        'near-neutral-s': 'not-stable' if consider_neutral_as_not_stable else 'stable',
        'neutral+': 'not-stable',
        'extremely-stable': 'stable',
        'extremely-unstable': 'not-stable'
    }

    simplify_ri = {
        'extremely-unstable': 'not-stable',
        'very-unstable': 'not-stable',
        'unstable': 'not-stable',
        'weakly-unstable': 'not-stable',
        'near-neutral-u': 'not-stable',
        'near-neutral-s': 'not-stable' if consider_neutral_as_not_stable else 'stable',
        'weakly-stable': 'stable',
        'stable': 'stable',
        'very-stable': 'stable',
        'extremely-stable': 'stable'
    }

    # ToDo: confirm what should be the decision for heat flux based approaches?
    simplification_dict = simplify_mol if stab_method=='mol' else simplify_ri
    return simplification_dict[stab_class] if stab_class in simplification_dict.keys() else 'unknown'