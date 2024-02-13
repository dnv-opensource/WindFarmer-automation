# ### WindFarmer API Blockage demo notebook
#
# The WindFarmer API is a web API. You can call it from any coding language, or use tools like Postman. There is an OpenAPI definition which provides
# documentation, and allows client code to be generated.
# 
# From python you can call the API directly, using `urllib3` or `requests`.
# 
# ## Using the API directly
# First, import the necessary modules
#%%
import os
import requests
import json
import time

# To access the API you need a authorization token. This should be kept secure - and not added to source control, so I'm getting it from an environment variable.
# The token should be passed as an Authorization header. We also need to set the `Content-Type` to let the API know that we're sending JSON data.
api_url = 'https://windfarmer.dnv.com/api/v1/'
auth_token = auth_token = os.environ['WINDFARMER_ACCESS_KEY']

headers = {
    'Authorization': f'Bearer {auth_token}',
    'Content-Type': 'application/json'
}

# ### Call `Status`
# Try calling the `Status` endpoint. This verifies that you can access the API and that your token is valid.
response = requests.get(api_url + 'Status', headers = headers)
print(f'Response from Status: {response.status_code}')
print(response.text)


# ### Call `BlockageCorrection`

# Prepare the input data for the BlockageCorrection calculation. This could come from elsewhere in your script, but here we're just loading it from a file.
dirname = os.path.dirname(__file__)
with open(os.path.join(dirname, 'input\BlockageCorrection_input_data.json')) as f:
    json_string = f.read()
    input_data = json.loads(json_string)

print(json_string[0:500] +  '...')

# The data is now in a dictionary...
print('Turbine 1 easting = ' + str({input_data['turbines'][1]['easting_m']}))

# Send the input data to the Blockage Correction calculation
start = time.time()
response = requests.post(
    api_url + 'BlockageCorrection', 
    headers=headers,
    json = input_data)
    
print(f'Response from BlockageCorrection {response.status_code} in {time.time() - start:.2f}s')

# Deserialize the response, and use it...
result = json.loads(response.content)
blockage_correction = float(result['blockageEffect'])* 100
print(f"Blockage correction efficiency = {blockage_correction:.3f} % ")
