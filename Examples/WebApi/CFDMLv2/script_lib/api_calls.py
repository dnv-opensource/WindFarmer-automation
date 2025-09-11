from typing import Tuple
import requests
import json
import asyncio
import time
import random
from pprint import pprint as pp

class WindFarmerAPI:
    """
    A class to manage WindFarmer API calls, with methods for synchronous and asynchronous calls.
    """
    def __init__(self, 
                 auth_token: str,
                 api_url: str = 'https://windfarmer.dnv.com/api/v2/'):
        """
        Initialize the WindFarmerAPI class
        :param api_url: The base URL for the WindFarmer API
        :param auth_token: The authentication token for the WindFarmer API.
        """
        self.api_url = api_url
        self.auth_token = auth_token
        self.get_status()

    def print_errors(response):
        response_json = json.loads(response.content)
        if (detail := response_json.get("detail")):
            print(f"Bad request: {detail}")
        if (errors := response_json.get("errors")):
            print("Errors:")
            pp(errors)

    def get_status(self):
        """ 
        Check the status of the WindFarmer API, confirming the validity of your access key and the API version.
        :return: None
        """
        response = requests.get(self.api_url + 'Status', headers = self._get_call_header())
        print(f'Response from Status: {response.status_code}')
        if response.status_code == 200:
            text = json.loads(response.text)
            print(f'{text["message"]} You are ready to run calculations!')
            print(f'  WindFarmer API version = {text["windFarmerServicesAPIVersion"]}')
            print(f'  Calculations version = {text["calculationLibraryVersion"]}')
        else:
            print(response.text)
            print('Check your access key is saved in the environment variable specified above, and up to date')

    async def call_aep_api(self, input_data: dict) -> dict:
        """
        Call the WindFarmer API to get the annual energy production.
        This function decides whether to call the synchronous or asynchronous API based on the number of turbines.
        param input_data: The input data for the API call.
        :return: The energy calculation results
        """
        turbines = []
        for farm in input_data["windFarms"]:
            for turbine in farm["turbines"]:
                turbines.append(turbine)
        number_of_turbines = len(turbines)
        
        print(f'Calling asynchronous AEP API')
        time_per_turbine = 1200 / 1000
        min_polling_interval_seconds = number_of_turbines * time_per_turbine / 5
        results = await self.call_aep_api_async(input_data, min_polling_interval_seconds)
        return results
    
    async def get_jobstatus(self, job_id: str) -> Tuple[str, str, str]:
        """Get the status of a job from the WindFarmer API.
        :param job_id: The ID of the job to check.
        """
        params = {}
        params["jobId"] = job_id
        result =  requests.get(self.api_url + 'AnnualEnergyProductionAsync', 
                               headers=self._get_call_header(), params= params)
        result_json = json.loads(result.content)
        # Get the status details from the response, if present
        message = result_json['message'] if 'message' in result_json else None
        stage_message = result_json['stageMessage'] if 'stageMessage' in result_json else None
        progress = str(result_json['progress']) + '%' if 'progress' in result_json else None

        # Combine the status details into a single string
        progress_message = ' - '.join([x for x in [progress, stage_message, message] if x])
        return (result_json['status'], progress_message, result_json['results'] if 'results' in result_json else None)

    async def poll_for_status(self, job_id: str, min_polling_interval_seconds = 20, start_time = None) -> Tuple[str, str, str]:
            """Poll the WindFarmer API for the status of an asynchronous job.
            It will return PENDING, RUNNING, SUCCESS or FAILED.
            If success, it will return the results of the calculation.  
            :param job_id: The ID of the job to poll.   
            :param min_polling_interval_seconds: The interval between polling calls in seconds.
            """
            if start_time == None:
                start_time = time.time()
            status = "PENDING"
            await ( asyncio.sleep(random.random() + 5))
            while(status == 'PENDING' or status == 'RUNNING'):
                (status, message, results ) = await self.get_jobstatus(job_id)
                if status == 'PENDING':
                    print("...Calculation queued and waiting to start")
                else:
                    print(f'...Calculation status @ {time.time() - start_time:.2f}s: {status} - {message}')
                await ( asyncio.sleep(random.random() + min_polling_interval_seconds))
            return status, message, results

    async def call_aep_api_async(self, input_data:dict, min_polling_interval_seconds: int = 20) -> dict:
        """
        Call the WindFarmer API asynchronously to get the annual energy production.
        Aynchronous calculations are slower, given startup overheads, but reliable for long running calculations as we implement a job queue.
        """
        start = time.time()
        job_id_response = requests.post(
            self.api_url + 'AnnualEnergyProductionAsync', 
            headers=self._get_call_header(),
            json = input_data)    
        print(f'Response {job_id_response.status_code} - {job_id_response.reason} in {time.time() - start:.2f}s')
        # Print the error detail if we haven't receieved a 200 OK response
        if job_id_response.status_code != 202:
            self.print_errors(job_id_response)
            raise Exception("Failed to submit AEP job")
        else:
            job_ID = json.loads (job_id_response.text)["jobId"]
            print ('...Job submitted with ID: ')
            print (job_ID)
            status, message, results = await self.poll_for_status(job_ID, min_polling_interval_seconds )
            if status == 'FAILED':
                print(f'Calculation failed: {message}')
                raise Exception(f"Calculation failed: {message}")
            print(f'{status} in {time.time() - start:.2f}s')
            return results

    def call_aep_api_sync(self, input_data: dict) -> dict:
        """
        Synchronous calculations are faster, but not supported for the largest wind farms:
        """
        start = time.time()
        response = requests.post(
            self.api_url + 'AnnualEnergyProduction', 
            headers=self._get_call_header(),
            json = input_data)
        print(f'Response {response.status_code} - {response.reason} in {time.time() - start:.2f}s')

        if response.status_code == 200:
            results = json.loads(response.content)
            return results
        else:
            # Print the error detail if we haven't receieved a 200 OK response 
            self.print_errors(response)
            return None
        
    def _get_call_header(self) -> dict:
        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Content-Type': 'application/json'
            }
        return headers
