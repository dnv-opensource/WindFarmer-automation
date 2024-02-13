# Ensure you have in the workbook
# - All turbine locations defined with valid turbine types in each scenario
# - Calculations are set up with appropriate settings
# - Consider whether you want to recalculate wind flow. This can take a long time for some grid setups and may be unecessary.
	def Execute(self):
		# Script starts here
		import os
		import shutil
		
		recalculate_flow = False
		recalculate_power_time_series = False

		Toolbox.Log( 'Starting calculations to update results', LogLevel.Warn)
		
		# Create a results directory
		folder_path = os.path.dirname( Toolbox.CurrentWorkbookPath)
		base_workbook_name = os.path.basename(Toolbox.CurrentWorkbookPath)
		
		for layoutScenario in Workbook.LayoutScenarios:
			Toolbox.ActivateLayoutScenario(layoutScenario)

			current_scenario_name = layoutScenario.Name
			results_folder = os.path.join(folder_path, str.format('results_for_{0}', current_scenario_name))
			if os.path.exists(results_folder):
				shutil.rmtree(results_folder)
			os.mkdir(results_folder )
			Toolbox.Log('Results directory = ' + results_folder)	
			
			if recalculate_flow:
				# Wind flow updates, including forestry
				Toolbox.Log( 'Updating wind flow calculation')
				if Workbook.Geography.ForestryGrids != None:
					Toolbox.CalculateForestryDisplacementHeights()
					Toolbox.Log( 't Calculated displacement heights')
				
				# set flow model type, according to available licence
				if (Toolbox.IsWaspAvailable(WAsPVersion.Version12) == WAsPStatus.Available):
					Toolbox.Log('t running WAsP 12 flow model')
					Workbook.ModelSettings.FlowSettings.FlowModelType = FlowModelType.WaspFromFreqDist
					Workbook.ModelSettings.FlowSettings.WAsPParameters.WAsPVersion = WAsPVersion.Version12
				else:
					Toolbox.Log('\t running simple flow model')
					Workbook.ModelSettings.FlowSettings.FlowModelType = FlowModelType.Simple
				Toolbox.CalculateWindFlow()
				Toolbox.Log( 'Calculated wind flow')
			
			
			# Wake and full AEP calculation
			Toolbox.CalculateEnergy()
			Toolbox.Log( 'Calculated Energy')
			
			# Power time series calculation - only needed for Net energy if you want to simulate time dependent effects
			if recalculate_power_time_series:
				Toolbox.CalculatePowerTimeSeries()
			
			# Net energy calculation
			Toolbox.RunMonteCarloEnergyAnalysis()
			Toolbox.Log( 'Calculated Net Energy')		
			
			# Export results
			tsv_folder = os.path.join(results_folder, 'TSVs')
			os.mkdir(tsv_folder )
			Toolbox.ExportResultsTsvFiles(tsv_folder)
			Toolbox.ExportEpaReport(os.path.join(results_folder, 'Results.docx'))
			Toolbox.ExportWorkbookResultsJson(os.path.join(results_folder, 'Results.json'))
			Toolbox.Log( str.format('Exported results to {0} for scenario {1}', results_folder, layoutScenario.Name ))
			