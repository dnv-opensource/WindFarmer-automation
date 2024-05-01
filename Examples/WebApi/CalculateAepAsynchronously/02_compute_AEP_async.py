# Example asynchronous calls to the API, 
# using pre-defined json files to describe the input
import aiohttp
import asyncio
import time
import os
import json

# API connection settings
BASE_URL = 'https://windfarmer.dnv.com/api/v2/'
BEARER_TOKEN = os.environ['WINDFARMER_ACCESS_KEY']

headers = {
    'Authorization': f'Bearer {BEARER_TOKEN}',
    'Content-Type': 'application/json'
}

# Input JSON files
script_dir_name = os.path.dirname(__file__) # Note it is better not to use os.path.curdir as it changes depending on whether running as a notebook or python script 
api_inputs_folder = os.path.join(script_dir_name, 'AEPInputsJson')

# Define a method to call the API 
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
        call_id = 0
        for filename in os.listdir(api_inputs_folder):
            with open(os.path.join(api_inputs_folder, filename)) as f:
                input_data = json.load(f)
                tasks.append(asyncio.ensure_future(call_api(session, 'AnnualEnergyProduction', call_id, input_data)))
                call_id += 1

        all_results = await asyncio.gather(*tasks)
        for result in all_results:
            full_energy_yield = result['windFarmAepOutputs'][0]['fullAnnualEnergyYield_MWh_per_year']
            print(f"Full annual energy yield: {full_energy_yield / 10e3:.2f} GWh/year")

start_time = time.time()
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())    
print(f'--- {time.time() - start_time:.2f} seconds ---')            

