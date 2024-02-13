# %% 
# # WindFarmer web API / BlockageCorrection demo
# The WindFarmer API is a web API. You can call it from any coding language, or use tools like Postman. 
# 
# There is an OpenAPI definition which provides
# documentation, and allows client code to be generated.
# 
# From python you can call the API directly, using `urllib3` or `requests`, or you can use the generated library.
# 
 
# ## Import packages
# First, import the necessary modules

import requests
import json
import os
import pandas as pd
import matplotlib.pyplot as plt

# %% 
# ## Get URL and API key
# To access the API you need a authorization token. This should be kept secure - and not added to source control, so I'm getting it from an environment variable.
# 
# The token should be passed as an Authorization header. We also need to set the `Content-Type` to let the API know that we're sending JSON data.

api_url = 'https://windfarmer.dnv.com/api/v1/'
auth_token = auth_token = os.environ['WINDFARMER_ACCESS_KEY']
# api_url = 'https://windfarmer.uat.dnv.com/api/v1/'
# auth_token = os.environ['WINDFARMER_UAT_KEY']

headers = {
    'Authorization': f'Bearer {auth_token}',
    'Content-Type': 'application/json'
}

# %% 
# ## User inputs
# In this example, we load data from files that match 2 files accepted by the blockage web app:
# * The power curve, thrust curve, and frequency distribution
# * The layout

# Input JSON files
script_dir_name = os.path.dirname(__file__) # Note it is better not to use os.path.curdir as it changes depending on whether running as a notebook or python script 
inputs_folder = os.path.join(script_dir_name, 'input')

pc_filename = os.path.join(inputs_folder, 'BlockageWebAppInputs', 'PowerCurve.txt')
layout_filename =  os.path.join(inputs_folder, 'BlockageWebAppInputs', 'Layout.txt')
significant_atmospheric_stability = True

# %% 
# ## Show layout and power curve
# 
# Here we parse the tab-separated input files and show the data for visual checking.
pc_df = pd.read_csv(pc_filename, sep='\t')
print("The power curve, thrust curve, and frequency distribution")
#display(pc_df)

turbines_df = pd.read_csv(layout_filename, sep='\t')
print("Layout")
#display(turbines_df)

# %%
print("Map of layout colored by hub height, with dots sized by rotor diameter (not to scale):")
plt.scatter(turbines_df['easting_m'], turbines_df['northing_m'], 
            c=turbines_df['hubHeight_m'], s=turbines_df['rotorDiameter_m'] * 4, cmap='BuGn');
plt.colorbar();
plt.xlabel("Easting [m]");
plt.ylabel("Northing [m]");
plt.show()

# %%
print("Power curve used in calculation:")
plt.plot(pc_df['windSpeed_m_per_s'], pc_df['powerOutput_kW']);
plt.xlabel("Wind speed [m/s]")
plt.ylabel("Power [kW]");
plt.show()

# %%
print("Thrust curve used in calculation:")
plt.plot(pc_df['windSpeed_m_per_s'], pc_df['thrustCoefficient']);
plt.xlabel("Wind speed [m/s]")
plt.ylabel("Thrust [Ct]");
plt.show()

# %%
print("Frequency distribution used in calculation:")
plt.plot(pc_df['windSpeed_m_per_s'], pc_df['frequency_pc']);
plt.xlabel("Wind speed [m/s]")
plt.ylabel("Frequency [%]");
plt.show()

# %%
# ## Convert DataFrames to lists for API
# The json input to the API can be built very simply from data frames.
# The data structure needed to serialise to json is formed of dictionaries and lists.

pc_dict_list = []
for index, row in pc_df.iterrows():
    pc_dict_list.append(row.to_dict())
pc_dict_list[0:3]


turbines_dict_list = []
for index, row in turbines_df.iterrows():
    turbines_dict_list.append(row.to_dict())
turbines_dict_list[0:3]


# %%
# ## Calculate blockage
input = {"turbines": turbines_dict_list,
         "turbinePerformance": pc_dict_list,
         "significantAtmosphericStability": significant_atmospheric_stability}

response = requests.post(
    api_url + 'BlockageCorrection', 
    headers=headers,
    json = input)

result = json.loads(response.content)
blockage_correction = float(result['blockageEffect']) *100

print(f"blockage correction = {blockage_correction:.3f} %")


