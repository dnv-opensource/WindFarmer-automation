	# Example layout iteration script
	def Execute(self):
		resultString = "Results: \n"

		for layoutScenario in Workbook.LayoutScenarios:
			Toolbox.ActivateLayoutScenario(layoutScenario)
			
			# Define some calculation settings
			energySettings = Workbook.ModelSettings.EnergySettings
			energySettings.WakeModelType = WakeModelType.EddyViscosity
			energySettings.ApplyLargeWindFarmCorrection = True
			energySettings.CalculationToUse = EnergyCalculationToUseType.New
			energySettings.CalculateEfficiencies = False
			energySettings.LargeWindFarmCorrectionSettings.BaseRoughness = 0.0002
			energySettings.LargeWindFarmCorrectionSettings.IncreasedRoughness = 0.0192
			energySettings.LargeWindFarmCorrectionSettings.DistanceInDiametersToStartOfRecovery = 120
			energySettings.NumberOfDirectionSectors = 180

			# Compute energy
			Toolbox.Log("Computing energy for layout scenario " + layoutScenario.Name, LogLevel.Warn)

			Toolbox.CalculateEnergy()

			Toolbox.Log("Finished energy calculation!", LogLevel.Warn)

			# Get results
			resultsScenario = Workbook.CurrentScenario
			subjectWindFarm = [ w for w in resultsScenario.WindFarms if w.IsNeighbour == False][0]
			Toolbox.Log("subject wind farm is: " + subjectWindFarm.Name, LogLevel.Warn)

			fullYield = resultsScenario.FarmTotalYields.GetVariantResult("Full").GetValueForFarm(subjectWindFarm).Value / 10e6	
			result = str.format("Net yield for scenario {0}:\t{1:.2f} GWh/annum\n", layoutScenario.Name, fullYield.ToString())
			Toolbox.Log(result, LogLevel.Warn)
			resultString += result

		Toolbox.Log(resultString)
		Toolbox.Log("END OF SCRIPT\n", LogLevel.Warn)
		