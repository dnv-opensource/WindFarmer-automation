# Example asynchronous calls to the API, 
# modifying a single json file to describe the input by deleting one turbine at a time
import aiohttp
import asyncio
import time
import os
import json

number_of_tests = 10

# API connection settings
BASE_URL = 'https://windfarmer.dnv.com/api/v2/'
BEARER_TOKEN = os.environ['WINDFARMER_ACCESS_KEY']

headers = {
    'Authorization': f'Bearer {BEARER_TOKEN}',
    'Content-Type': 'application/json'
}

# Input JSON files
script_dir_name = os.path.dirname(__file__) # Note it is better not to use os.path.curdir as it changes depending on whether running as a notebook or python script 
api_inputs_file = os.listdir(os.path.join(script_dir_name, 'AEPInputsJson'))[0]
api_inputs_file_path = os.path.join(script_dir_name, 'AEPInputsJson', api_inputs_file)
print(f'calculating using {api_inputs_file} as input')

# Define an asynchronous method to call the API 
async def call_api(session, api_name, id, data):
    print(f'{api_name} - call {id}')
    
    async with session.post(
        BASE_URL + api_name,
        headers = headers,
        json = data) as resp:
        
        result = await resp.json()
        print(f'{api_name} - call {id} complete with status {resp.status}')
        return result

# Generate and make the API calls
async def main():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(0, number_of_tests):
            with open(api_inputs_file_path) as f:
                input_data = json.load(f)
                # delete one turbine to generate a new test case
                del input_data['windFarms'][0]['turbines'][i]
                tasks.append(asyncio.ensure_future(call_api(session, 'AnnualEnergyProduction', i, input_data)))

        all_results = await asyncio.gather(*tasks)
        for result in all_results:
            full_energy_yield = result['windFarmAepOutputs'][0]['fullAnnualEnergyYield_MWh_per_year'] / 10e3
            print(f"Full annual energy yield: {full_energy_yield:.2f} GWh/year")

start_time = time.time()
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())    
print(f'--- {time.time() - start_time:.2f} seconds ---')            