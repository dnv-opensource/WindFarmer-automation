import os
from datetime import timedelta as td
import time
import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import interp1d

R_E = 6371.229e3
G = 9.80665

def slice_and_compute(ds, vars, latitude, longitude, start, end):
    sliced = ds[vars] \
        .sel(latitude=latitude, longitude=longitude, method='nearest') \
        .sel(valid_time=slice(start, end))
    print("\t\tSize of the slice: {} kB".format(sliced.nbytes / 1024))
    return sliced.compute().to_dataframe().drop(['depthBelowLandLayer','entireAtmosphere', 'number', 'surface'], axis=1, errors='ignore')

def get_era5_temp_and_wind_speed_at_pressure_levels_as_df(PAT, latitude, longitude, start, end):
    """
    Get the ERA5 wind speed and temperature at pressure level data for a specific location and time span.

    Parameters
    ----------
    PAT : a string
        The personal access token for the Earth Data Hub API.
    latitude : a float
        The latitude of the location of interest.
    longitude : a float
        The longitude of the location of interest.
    start : a datetime.datetime
        The start of the time span of interest.
    end : a datetime.datetime
        The end of the time span of interest.
        
    Returns
    -------
    subset_df : a pandas.DataFrame
        The subset of the ERA5 wind speed and temperature at pressure level data for a specific location and time span.

    """
    ds = get_era5_pressure_level_dataset(PAT)
    variables = ['t', 'z']
    ds = ds.sel(isobaricInhPa=[1000,  925])
    df = get_era5_subset_as_df(ds, variables, latitude, longitude, start, end)
    df['alt'] = R_E * (df['z'] / 9.80665) / (R_E - df['z'] / 9.80665)
    df['t_c'] = df['t'] - 273.15

    return df

def get_era5_signal_names_for_heat_flux_method():
    """
    Gets the surface sensible heat flux ERA5 signal name required to download a heat flux metric suitable for classifying stability
    """
    return ['sshf']

def get_era5_signal_names_for_mol_method():
    """
    Gets the list of ERA5 signal names required to download to define a time series of Monin Obhukhov Length
    
    To calculate MOL, we follow an ECMWF recipe available https://confluence.ecmwf.int/display/CKB/ERA5%3A+How+to+calculate+Obukhov+Length
    which directly references the instantaneous fluxes ( inss , iews, ishf)
    """
    return ['t2m', 'd2m', 'sp', 'ishf', 'ie', 'inss', 'iews']

def get_era5_signal_names_for_blended_mol_hf_method():
    """
    Gets the list of ERA5 signal names required to download to define a time series of Monin Obhukhov Length
    and also the hf method. 
    """
    mol_signals = get_era5_signal_names_for_mol_method()
    # Note we currently use different heat flux signals for the MOL calculation (instantantanious) to the heat flux only approach
    hf_signals = get_era5_signal_names_for_heat_flux_method()
    return hf_signals + mol_signals

def get_era5_signal_names_for_richardson_number_method():
    """
    Gets the list of ERA5 signal names required to download to define a time series of Richardson Number
    """
    return ['u10', 'v10', 'u100', 'v100', 'skt', 'blh', 'z']
    
def get_era5_stability_related_signals_on_model_levels_as_df(PAT, latitude, longitude, start, end):
    """
    Get the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span.

    Parameters
    ----------
    PAT : a string
        The personal access token for the Earth Data Hub API.
    latitude : a float
        The latitude of the location of interest.
    longitude : a float
        The longitude of the location of interest.
    start : a datetime.datetime
        The start of the time span of interest.
    end : a datetime.datetime   
        The end of the time span of interest.

    Returns
    -------
    subset_df : a pandas.DataFrame
        The subset of the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span.
    """
    ds = get_era5_model_level_dataset(PAT)
    variables_mol = get_era5_signal_names_for_mol_method()
    variables_ri = get_era5_signal_names_for_richardson_number_method()
    variables_hf = get_era5_signal_names_for_heat_flux_method()
    variables = variables_mol + variables_ri + variables_hf

    return get_era5_subset_as_df(ds, variables, latitude, longitude, start, end)

def get_era5_subset_as_df(ds, variables, latitude, longitude, start, end):
    """
    Get a subset of the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span.

    Parameters
    ----------
    ds : an xarray.Dataset
        The ERA5 single level data (link to the dataset).
    variables : a list of strings
        The variables of interest.
    latitude : a float
        The latitude of the location of interest.
    longitude : a float
        The longitude of the location of interest.
    start : a datetime.datetime
        The start of the time span of interest.
    end : a datetime.datetime
        The end of the time span of interest.

    Returns
    -------
    subset_df : a pandas.DataFrame
        The subset of the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span.
    """

    xr.set_options(keep_attrs=True)
    download_window = 360# days
    number_of_vars_per_request = 5

    # loading more than 6month was occassionally timing out, so breaking the load into chunks:
    time_slices = [x.to_datetime64() for x in pd.date_range(start=start, 
                                                            periods=np.ceil((end-start)/td(days=download_window)).astype(int),
                                                            freq='{}ME'.format(int(download_window/30)), inclusive='both')]
    if len(time_slices) == 1:
        time_slices = [np.datetime64(start), np.datetime64(end)]
    if time_slices[-1] > np.datetime64(end):
        time_slices[-1] = np.datetime64(end)
    if time_slices[0] > np.datetime64(start):
        time_slices.insert(0, np.datetime64(start))
    # correct longitude to be in the range 0-360 (ERA5 convention)
    if longitude < 0:
        longitude = 360 + longitude

    # time loop (we don't want to download more than 6 months at a time, because the requests tended to time out)
    time_chunks = []

    variables = np.unique(variables).tolist()

    for i in range(len(time_slices)-1):
        print("loading time slice {} to {}".format(time_slices[i], time_slices[i + 1]))
        vars_iterator = iter(variables)
        var_chunks = []
        while True:
            vars_batch = []
            try:
                for _ in range(number_of_vars_per_request):
                    vars_batch.append(next(vars_iterator))
            except StopIteration:
                if not vars_batch:
                    break  # Exit the while loop if no more items in the iterator
            print("\tloading variables: {}".format(vars_batch))
            start_time = time.time()
            var_chunks.append(slice_and_compute(ds, vars_batch, latitude, longitude, time_slices[i], time_slices[i + 1]))
            end_time = time.time()
            print("\t\tExecution time: {:.2f} seconds".format(end_time - start_time))
            
        time_chunks.append(pd.concat(var_chunks, axis=1))

    subset_df = pd.concat(time_chunks, axis=0)
    subset_df.name = "{}_{}".format(latitude, longitude)
    return subset_df

def get_era5_model_level_dataset(PAT):
    """
    Get the ERA5 single level data.
    Parameters
    ----------
    None
    
    Returns
    -------
    ds : an xarray.Dataset
        The ERA5 single level data.
    Notes
    -----
    The function uses the Earth Data Hub API to access the ERA5 single level data.
    """
    ds = xr.open_dataset(
        f"https://edh:{PAT}@data.earthdatahub.destine.eu/era5/reanalysis-era5-single-levels-v0.zarr",
        chunks={},
        engine="zarr",
        storage_options = {'verify_ssl': False}
    )
    return ds

def get_era5_pressure_level_dataset(PAT):
    """
    Get the ERA5 pressure level data.
    Parameters
    ----------
    None
    
    Returns
    -------
    ds : an xarray.Dataset
        The ERA5 pressure level data.
    Notes
    -----
    The function uses the Earth Data Hub API to access the ERA5 pressure level data.
    """

    ds = xr.open_dataset(
        f"https://edh:{PAT}@data.earthdatahub.destine.eu/era5/reanalysis-era5-pressure-levels-v0.zarr",
        chunks={},
        engine="zarr",
        storage_options = {'verify_ssl': False}

    )
    return ds

def qswat(t, p):
    """
    Computes saturation q (with respect to water)
    In  t   : Temperature                   (K)
        p   : Pressure                      (Pa)
    Out qswt: Saturation specific humidity  (kg/kg)

    taken from ERA5 docs: https://confluence.ecmwf.int/display/CKB/ERA5%3A+How+to+calculate+specific+humidity+from+relative+humidity
    """
    rkbol = 1.380658e-23
    rnavo = 6.0221367e+23
    r = rnavo * rkbol
    rmd = 28.9644
    rmv = 18.0153
    rd = 1000 * r / rmd # Gas constant for air
    rv = 1000 * r / rmv # Gas constant for water vapour
    restt = 611.21
    r2es = restt * rd / rv
    r3les = 17.502
    r4les = 32.19
    retv = rv / rd - 1  # Tv = T(1+retv*q)
    rtt = 273.16        # Melting point (0 Celcius)
    foeew = r2es * np.exp((r3les * (t - rtt)) / (t - r4les))
    qs = foeew / p
    zcor = 1 / (1 - retv * qs)
    qs = qs * zcor
 
    return qs

def calculate_obukhov_length(data):
    """
    Calculate the Obukhov length.
    as per ERA5 docs: https://confluence.ecmwf.int/display/CKB/ERA5%3A+How+to+calculate+Obukhov+Length

    Parameters
    ----------
    data : an pandas.DataFrame being a slice of the full ERA5 single level data (for a specific location and time span)
        set served up by Earth Data Hub under URL: data.earthdatahub.destine.eu/era5/reanalysis-era5-single-levels-v0.zarr
    
    Returns
    -------
    L : an pandas.Series
        The calculated Obukhov length time series.
    Notes
    -----
    {Additional notes or references, if any}
    
    """
    vk = 0.4 # VonKarman constant
    g = G # Gravity acceleration
    retv = 0.6078 # Tv = T*(1+retv*q)
    rd = 287.06 # Gas constant
    cp = 1004.7 # Air heat capacity at constant pressure
    
    q2 = qswat(data['d2m'], data['sp']) # q2 is saturation value at 2d
    tv2 = data['t2m'] * (1 + retv * q2) # Virtual temperature
    rho = data['sp'] / (rd * tv2) # Air density
    tau = np.sqrt(data['iews']**2 + data.inss**2) # Turb. surface stress
    ust = np.maximum(np.sqrt(tau / rho), 0.001) # Friction velocity
    wt = -data['ishf'] / (rho * cp)  # Turbulent heat flux
    wq = -data['ie'] / rho # Turbulent moisture flux
    wtv = wt + retv * data['t2m'] * wq # Virtual turbulent heat flux
    tvst = -wtv / ust # Turbulent temperature scale
    Linv = vk * g * tvst / (tv2 * ust**2) # Inverse Obukhov length, Stull eq. (5.7c)
    
    L = 1 / Linv

    return L

def _interpolate_pressure_level_data_to_100m_and_150m(data_at_pressure_levels, data_at_single_levels):
    """
    Pressure level interpolation to create signal data at heights relevant to Richardson number calculations
    """
    # Define the pressure levels you want to interpolate between
    pressure_levels = [1000, 925]

    # interpolate temperature & wind speed at fixed altitudes
    signals = ['t']#, 'u', 'v']
    interpolated_signals = {}

    for signal in signals:
        for altitude in [2.0, 30.0, 100.0, 150.0]:
            data = data_at_pressure_levels.loc[(slice(None), pressure_levels), signal].unstack(level=1)
            data = pd.concat([data_at_single_levels['t2m'], data], axis=1)
            alt = data_at_pressure_levels.loc[(slice(None), pressure_levels), 'alt'].unstack(level=1)
            alt = pd.concat([pd.Series(2.0, index=data.index), alt], axis=1)
            interpolated = pd.Series(data.index.map(lambda x: interp1d(alt.loc[x,:], data.loc[x, :], fill_value="extrapolate")(altitude)),                                 index=data.index)
            interpolated_signals[f"{signal}_{int(altitude)}"] = interpolated
    
    return pd.DataFrame(interpolated_signals)

def _calculate_bulk_richardson_number( height_difference_m, upper_temperature_K, lower_temperature_K, u_wind_vector, v_wind_vector ):
    """
    Calculate the bulk Richardson number.
    as per publication: J Sanz Rodrigo et al 2015 J. Phys.: Conf. Ser. 625 012044 https://doi.org/10.1088/1742-6596/625/1/012044, Eq.(8)

    Parameters
    ----------
    height_difference_m : difference in height between the upper and lower temperature signals
    upper_temperature_K : higher altitude temperature signal [K]
    lower_temperature_K : lower altitude temperature signal [K]
    u_wind_vector : u component of wind speed [m/s]
    v_wind_vector : v component of wind speed [m/s]
    
    Returns
    -------
    ri : an pandas.Series
        The calculated bulk Richardson number time series.
    """
   
    g = G
    ri = g * height_difference_m * (upper_temperature_K - lower_temperature_K) / (lower_temperature_K * (u_wind_vector**2 + v_wind_vector**2))
    return ri

def _calculate_bulk_richardson_number_at_100m(data):
    """
    Calculate the bulk Richardson number.
    as per publication: J Sanz Rodrigo et al 2015 J. Phys.: Conf. Ser. 625 012044 https://doi.org/10.1088/1742-6596/625/1/012044, Eq.(8)

    Parameters
    ----------
    data : a pandas.DataFrame being a slice of the full ERA5 single level data (for a specific location and time span)
        set served up by Earth Data Hub under URL: data.earthdatahub.destine.eu/era5/reanalysis-era5-single-levels-v0.zarr
    
    Returns
    -------
    ri : an pandas.Series
        The calculated bulk Richardson number time series.
    """
    z = 100
    ri = _calculate_bulk_richardson_number( z, 
                                        upper_temperature_K= data['t_100'],
                                        lower_temperature_K= data['skt'],
                                        u_wind_vector=data['u100'],
                                        v_wind_vector=data['v100'])
    return ri

def _calculate_bulk_richardson_number_at_10m(data):
    """
    Calculate the bulk Richardson number.
    as per publication: J Sanz Rodrigo et al 2015 J. Phys.: Conf. Ser. 625 012044 https://doi.org/10.1088/1742-6596/625/1/012044, Eq.(8)

    Parameters
    ----------
    data : a pandas.DataFrame being a slice of the full ERA5 single level data (for a specific location and time span)
        set served up by Earth Data Hub under URL: data.earthdatahub.destine.eu/era5/reanalysis-era5-single-levels-v0.zarr
    
    Returns
    -------
    ri : an pandas.Series
        The calculated bulk Richardson number time series.
    """
    z = 2 #we fix the height between the two temperature point to be 2 m (surface and 2m above)
    ri = _calculate_bulk_richardson_number( z, 
                                        upper_temperature_K= data['t2m'],
                                        lower_temperature_K= data['skt'],
                                        u_wind_vector=data['u10'],
                                        v_wind_vector=data['v10'])
    return ri

def _calculate_bulk_richardson_number_between_30m_and_100m(data):
    """
    Calculate the bulk Richardson number.
    as per publication: J Sanz Rodrigo et al 2015 J. Phys.: Conf. Ser. 625 012044 https://doi.org/10.1088/1742-6596/625/1/012044, Eq.(8)

    Parameters
    ----------
    data : a pandas.DataFrame being a slice of the full ERA5 single level data (for a specific location and time span)
        set served up by Earth Data Hub under URL: data.earthdatahub.destine.eu/era5/reanalysis-era5-single-levels-v0.zarr
    
    Returns
    -------
    ri : an pandas.Series
        The calculated bulk Richardson number time series.
    """
   
    z = 70 #we fix the height between the two temperature point to be 2 m (surface and 2m above)
    ri = _calculate_bulk_richardson_number( z, 
                                        upper_temperature_K= data['t_100'],
                                        lower_temperature_K= data['t_30'],
                                        u_wind_vector=data['u100'],
                                        v_wind_vector=data['v100'])
    return ri

def get_classification_from_hf(hf_ts):
    """
    Classify the stability from a heatflux signal based on the sign of the signal.
    Parameters
    ----------
    hf_ts : an pandas.Series
        The heat flux time series.
    
    Returns
    -------
    classification : an pandas.Series
        The classification of the Obukhov length time series
    """
    classification = pd.cut(hf_ts, bins=[-np.inf, 0, np.inf],
                            labels=['unstable', 'stable'])
    return classification

def get_classification_from_mol(mol_ts):
    """
    Classify the Obukhov length.
    Parameters
    ----------
    mol_ts : an pandas.Series
        The calculated M-O length time series.
    
    Returns
    -------
    classification : an pandas.Series
        The classification of the Obukhov length time series
    Notes
    -----
    Follows the classification of Obukhov length assumed in https://www.researchgate.net/figure/Classification-of-atmospheric-stability-according-to-Monin-Obukhov-length-in-tervals_tbl1_266043126
    """
    classification = pd.cut(mol_ts, bins=[-np.inf, -500, -200, -100, -50, 0, 10, 50, 200, 500, np.inf],
                            labels=['neutral-', 'near-neutral-u', 'unstable', 'very-unstable', 'extremely-unstable', 'extremely-stable', 'very-stable', 'stable', 'near-neutral-s', 'neutral+'])
    # classification = pd.cut(mol_ts, bins=[-np.inf, -500, -200, -100, -50, 10, 50, 200, 500, np.inf],
    #                         labels=['neutral-', 'near-neutral-u', 'unstable', 'very-unstable', 'unknown', 'very-stable', 'stable', 'near-neutral-s', 'neutral+'])

    return classification

def get_classification_from_ri(ri_ts):
    """
    Classify the bulk Richardson number.
    Parameters
    ----------
    ri_ts : an pandas.Series
        The calculated bulk Richardson number time series.
    
    Returns
    -------
    classification : an pandas.Series
        The classification of the bulk Richardson number time series
    Notes
    -----
    Follows the classification of Richardson number as per publication: J Sanz Rodrigo et al 2015 J. Phys.: Conf. Ser. 625 012044 https://doi.org/10.1088/1742-6596/625/1/012044, Eq.(9), Table 1
    """
    def zeta_func(ri):
        c1 = 10.0
        c2 = 5.0
        temp1 = c1 * ri / (1 - c2 * ri)
        temp2 = c1 * ri
        if temp1 <= 0:
            return temp1
        else:
            return temp2 
        
    zeta = ri_ts.apply(zeta_func)
    classification = pd.cut(zeta, bins=[-np.inf, -2.0, -0.6, -0.2, -0.02, 0.0, 0.02, 0.2, 0.6, 2.0, np.inf],
                            labels=['extremely-unstable', 'very-unstable', 'unstable', 'weakly-unstable', 'near-neutral-u', 'near-neutral-s', 'weakly-stable', 'stable', 'very-stable', 'extremely-stable'])
    return classification

def append_stability_metric(subset_df_single_levels):
    """
    Append the stability metrics & derived wind direction to the ERA5 single level data subset.
    Parameters
    ----------
    subset_df : a pandas.DataFrame
        The subset of the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span.
    latitude : a float
        The latitude of the location of interest.
    longitude : a float
        The longitude of the location of interest.

    Returns
    -------
    subset_df : a pandas.DataFrame
        The subset of the ERA5 single level data, relevant for stability metric derivation, for a specific location and time span, with appended stability metrics.
    """
    def which_bin(dir_in_degs):
        no_right_bin_boundaries_smaller_than_dir = sum([dir_in_degs <= x  for x in bins])
        return 12-no_right_bin_boundaries_smaller_than_dir + 1 if no_right_bin_boundaries_smaller_than_dir != 0 else 1

    if all( signal in subset_df_single_levels.columns for signal in get_era5_signal_names_for_mol_method()):
        subset_df_single_levels['L'] = calculate_obukhov_length(subset_df_single_levels)
        subset_df_single_levels['classification_mol'] = get_classification_from_mol(subset_df_single_levels['L'])
    
    #Ri @10m
    if all( signal in subset_df_single_levels.columns for signal in get_era5_signal_names_for_richardson_number_method()):
        subset_df_single_levels['Ri10'] = _calculate_bulk_richardson_number_at_10m(subset_df_single_levels)
        subset_df_single_levels['classification_ri10'] = get_classification_from_ri(subset_df_single_levels['Ri10'])

    #surface heat flux
    if all( signal in subset_df_single_levels.columns for signal in  get_era5_signal_names_for_heat_flux_method()):
        subset_df_single_levels['classification_hf'] = get_classification_from_hf(subset_df_single_levels['sshf'] / 3600) # conversion from J/m2 to W/m2, doesn't matter for classification 

    if 't_100' in subset_df_single_levels.columns:
        # we don't need the Ri classification in the final solution, so skipping that if pressure level data hasn't been loaded
        #Ri @100m
        subset_df_single_levels['Ri100'] = _calculate_bulk_richardson_number_at_100m(subset_df_single_levels)
        subset_df_single_levels['classification_ri100'] = get_classification_from_ri(subset_df_single_levels['Ri100'])

        #Ri between 30m and 100m
        subset_df_single_levels['Ri30_100'] = _calculate_bulk_richardson_number_between_30m_and_100m(subset_df_single_levels)
        subset_df_single_levels['classification_ri30_100'] = get_classification_from_ri(subset_df_single_levels['Ri30_100'])


    #wind direction
    if all(signal in subset_df_single_levels.columns for signal in ['u10', 'v10']):
        subset_df_single_levels['wind_dir'] = (180 + 180 / np.pi * np.atan2(subset_df_single_levels['u10'], subset_df_single_levels['v10'])) % 360
        bins = [x for x in range(15, 360, 30)]
        subset_df_single_levels['dir_bin'] = subset_df_single_levels['wind_dir'].apply(which_bin)
    else:
        print("Can't derive wind direction - wind speed vectors u10 and v10 missing for site")

def load_era5_data_from_file(project_name, use_cached=False, era5_cache_directory='./era5_cache'):
    """
    Load the processed ERA5 data from previously cached file, 
    or do the processing & cache if use_cached==False.
    """
    if not use_cached:
        #load the raw outputs of the era5 download
        df = pd.read_csv(os.path.join(era5_cache_directory, f'era5_{project_name}.csv'), index_col=0)
        df.drop_duplicates(inplace=True)
        
        # # We don't intend to use the pressure level data approach at this time
        # # ToDo: delete?
        # if os.path.exists(os.path.join(era5_cache_directory, f'era5_pressure_levels_{project_name}.csv')):
        #     df_pressure_levels = pd.read_csv(os.path.join(era5_cache_directory, f'era5_pressure_levels_{project_name}.csv'), index_col=(0,1))
        #     df_pressure_levels.drop_duplicates(inplace=True)
        #     # interpolate at 100m and 150m and concat with the single level data
        #     data_interpolated_at_100m_and_150m = _interpolate_pressure_level_data_to_100m_and_150m(df_pressure_levels, df)
        #     df = pd.concat([df, data_interpolated_at_100m_and_150m], axis=1)

        # derive the stability metric & wind direction 
        append_stability_metric(df) #works regardless of whether pressure level data has been loaded or not
        df.to_csv(os.path.join(era5_cache_directory, f'era5_{project_name}_processed.csv'))
        return df
    else:
        temp = pd.read_csv(os.path.join(era5_cache_directory, f'era5_{project_name}_processed.csv'), index_col=0)
        temp.dropna(inplace=True, axis=0, how='any')
        return temp