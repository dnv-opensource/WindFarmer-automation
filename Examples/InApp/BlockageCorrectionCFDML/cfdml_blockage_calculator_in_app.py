	# Compute CFD.ML and BEET blockage correction efficiencies for your project
	def Execute(self):
		
		# User Settings
		gnn_type = "onshore" # "onshore" / "offshore"
		blockage_correction_application_method = "OnEnergy" # "OnWindSpeed" / "OnEnergy"
		relative_results_folder_path = "10.Energy\\03.Losses\\CFDMLBlockage" # path to results relative to workbook 
		envVariableName = "WINDFARMER_ACCESS_KEY" # See setup instructions for saving your access key as an environment variable: https://myworkspace.dnv.com/download/public/renewables/windfarmer/manuals/latest/WebAPI/Introduction/gettingStarted.html
		baseUrl = 'https://windfarmer.dnv.com/api/v2/' # CFD.ML available in v2
		number_of_direction_steps = 180

		# imports
		clr.AddReference('System')
		clr.AddReference('System.Net.Http')
		from System.Net.Http import HttpClient, Headers
		from System import Uri
		import os
		import shutil
		import json
		
		#Output folders
		workbook_folder_path = os.path.dirname( Toolbox.CurrentWorkbookPath)
		results_folder = os.path.join(workbook_folder_path, relative_results_folder_path)
		if os.path.exists(results_folder):
			shutil.rmtree(results_folder)
		os.mkdir(results_folder)
		Toolbox.Log(results_folder)
		
		# get access key
		accessKey = os.environ.get(envVariableName)
		if not accessKey:
			message = "Can't find access key in environment variable named {0}".format(envVariableName)
			Toolbox.Log( message ,LogLevel.Error)
			raise Exception(message)
		
		# HTTP client setup - this is a .NET client
		client = HttpClient()
		client.DefaultRequestHeaders.Authorization = Headers.AuthenticationHeaderValue("Bearer", accessKey)
		client.DefaultRequestHeaders.Accept.Add(Headers.MediaTypeWithQualityHeaderValue("application/json"))
		
		# Check we have a valid connection to the API
		Toolbox.Log("Computing CFD.ML blockage correction efficiency via WindFarmer's web API", LogLevel.Warn)
		Toolbox.Log("Check API connection, calling Status end point...")
		response_task =  client.GetAsync( Uri(baseUrl + "Status"))
		response_task.Wait()
		content_task = response_task.Result.Content.ReadAsStringAsync()
		content_task.Wait()                
		content = content_task.Result
		Toolbox.Log("..." + json.loads(content)["message"]);
		Toolbox.Log("...API version: " + json.loads(content)["windFarmerServicesAPIVersion"]);
				
		# Now make calles to the AEP API to derive blockage corrections
		Toolbox.Log("Calculate blockage corrections, calling the AEP web API end point...")
		
		# write out the project data as inputs to the AEP API, then load this JSON back into a dictionary
		input_data_file_path = os.path.join(results_folder, "AEPAPIInputs.json" )
		Toolbox.ExportWindFarmerEnergyJson( input_data_file_path )
		file = open(input_data_file_path, mode='r')            
		json_input_str = file.read()
		file.close()

		# general settings turning off all models other than blockage for speed
		json_input= json.loads(json_input_str)
		json_input['energyEfficienciesSettings']['numberOfDirectionSectorsForWakeCalculation'] = number_of_direction_steps
		json_input['energyEfficienciesSettings']['wakeModel']['wakeModelType'] = 'NoWakeModel'
		json_input["energyEfficienciesSettings"]["wakeModel"]["noWakeModel"]["useLargeWindFarmModel"] = False
		json_input["energyEfficienciesSettings"]["calculateEfficiencies"] = False
		json_input["energyEfficienciesSettings"]["includeHysteresisEffect"] = False
		json_input["energyEfficienciesSettings"]["includeTurbineManagement"] = False
		json_input["energyEfficienciesSettings"]["calculateIdealYield"] = False
		json_input["energyEfficienciesSettings"]["turbineFlowAndPerformanceMatrixOutputSettings"] = {}
		
		# Call API to compute blockages:
		# BEET 
		json_input['energyEfficienciesSettings']['blockageModel']['blockageModelType'] = "BEET" 
		json_input['energyEfficienciesSettings']['blockageModel']['beet']['blockageCorrectionApplicationMethod'] = blockage_correction_application_method
		# BEET Stable conditions
		json_input["energyEfficienciesSettings"]["blockageModel"]["beet"]["significantAtmosphericStability"] = True
		beet_stable_results, beet_stable_correction_efficiency = self.post_request(baseUrl + "AnnualEnergyProduction", json_input, "BEET-stable", results_folder, client, blockage_correction_application_method)
		# BEET Unstable conditions
		json_input["energyEfficienciesSettings"]["blockageModel"]["beet"]["significantAtmosphericStability"] = False
		beet_unstable_results, beet_unstable_correction_efficiency = self.post_request(baseUrl + "AnnualEnergyProduction", json_input, "BEET-unstable-neutral", results_folder, client, blockage_correction_application_method)
		
		# CFD.ML blockage 
		json_input['energyEfficienciesSettings']['blockageModel']['blockageModelType'] = "CFDML" 
		json_input['energyEfficienciesSettings']['blockageModel']['cfdml']['blockageCorrectionApplicationMethod'] = blockage_correction_application_method
		json_input["energyEfficienciesSettings"]["blockageModel"]["cfdml"]["cfdmlBlockageWindSpeedDependency"] = "FromBlockageExtrapolationCurve" 
		json_input["energyEfficienciesSettings"]["blockageModel"]["cfdml"]["cfdmlSettings"]["gnnType"] = gnn_type		
		cfdml_results, cfdml_correction_efficiency = self.post_request(baseUrl + "AnnualEnergyProduction", json_input, "CFD.ML", results_folder, client, blockage_correction_application_method)
		
		# Report results to word
		table = "Model \tAtmospheric Stability \tOnshore\\Offshore \tBlockage Correction Efficiency [%]"
		table += "\nBEET \tPredominantly Neutral and Unstable \tonshore \t{0:.3f} %".format(beet_unstable_correction_efficiency*100)
		table += "\nBEET \tSignificant atmospheric stability \tonshore \t{0:.3f} %".format(beet_stable_correction_efficiency*100)
		table += "\nCFD.ML \tNeutral \t{0} \t {1:.3f} %".format(gnn_type, cfdml_correction_efficiency*100)
		Toolbox.Log("Calculations Complete!\n" + table, LogLevel.Warn)
		Toolbox.MeasurementCampaign.InsertCustomText("Blockage caculation results", "WFHeading1")
		Toolbox.MeasurementCampaign.InsertCustomText("Workbook: {0}".format(Toolbox.CurrentWorkbookPath))
		Toolbox.MeasurementCampaign.InsertCustomText("Blockage correction application method: {0}".format(blockage_correction_application_method))
		Toolbox.MeasurementCampaign.InsertCustomTable(table, "WFSubTitlePlusNotes")
		report_name = os.path.join(results_folder, "CFDMLBlockageResults.docx")
		Toolbox.MeasurementCampaign.FlushReport( report_name )


	def get_blockage_efficiency(self, results_dict, blockage_correction_application_method):
		if blockage_correction_application_method == "OnEnergy":
			blockage_correction_efficiency = float(results_dict['weightedBlockageEfficiency'])
		elif blockage_correction_application_method == "OnWindSpeed":
			full_aep_MWh_per_year = sum([float(x['fullAnnualEnergyYield_MWh_per_year']) for x in results_dict['windFarmAepOutputs']])
			gross_aep_MWh_per_year = sum([float(x['grossAnnualEnergyYield_MWh_per_year']) for x in results_dict['windFarmAepOutputs']])
			blockage_correction_efficiency = full_aep_MWh_per_year / gross_aep_MWh_per_year
		else:
			Toolbox.Log("blockage_correction_application_method not recognised", LogLevel.Error)
		return blockage_correction_efficiency    

	# Function to make a POST request and return the result as a dictionary
	def post_request (self, url, json_input, model_name, results_folder, httpclient, blockage_correction_application_method):
		# imports
		clr.AddReference('System.Net.Http')
		from System.Net.Http import StringContent
		from System import Uri
		from System.Text import Encoding
		import os
		import json
		
		payload =  StringContent(json.dumps(json_input), Encoding.UTF8, "application/json")
		postResponse_task =  httpclient.PostAsync(Uri(url), payload)
		postResponse_task.Wait()
		postResponseContent_task =  postResponse_task.Result.Content.ReadAsStringAsync()
		postResponseContent_task.Wait()
		postResponseContent = postResponseContent_task.Result
		results_json = json.loads(postResponseContent)
		results_file_path = os.path.join(results_folder, "{0}BlockageResults.json".format(model_name) )
		with open(results_file_path, "w") as f:
			f.write(json.dumps(results_json, indent=1))
		# compute the correction efficiency	
		correction_efficiency = self.get_blockage_efficiency(results_json, blockage_correction_application_method)
		Toolbox.Log("{0} Blockage correction efficiencies= {1:.3f}%\t results written to file:\t{2}".format(model_name, correction_efficiency*100, results_file_path))
		return results_json, correction_efficiency
