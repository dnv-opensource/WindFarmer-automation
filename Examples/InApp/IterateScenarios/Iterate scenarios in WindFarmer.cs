/// <Summary>
/// Example layout iteration script
/// </Summary>
public void Execute()
{
	string resultString	= "Results: \n";
	
    foreach (LayoutScenario layoutScenario in Workbook.LayoutScenarios)
	{
		#region // Define some calculation settings
		var energySettings = Workbook.ModelSettings.EnergySettings;
		energySettings.WakeModelType = WakeModelType.EddyViscosity;
		energySettings.ApplyLargeWindFarmCorrection = true;
		energySettings.CalculationToUse = EnergyCalculationToUseType.New;
		energySettings.CalculateEfficiencies = false;
		energySettings.LargeWindFarmCorrectionSettings.BaseRoughness = 0.0002;
		energySettings.LargeWindFarmCorrectionSettings.IncreasedRoughness = 0.0192;
		energySettings.LargeWindFarmCorrectionSettings.DistanceInDiametersToStartOfRecovery = 120;
		energySettings.NumberOfDirectionSectors = 180;
		#endregion 
		
		// Compute energy
		Toolbox.Log("Computing energy for layout scenario " + layoutScenario.Name, LogLevel.Warn);
		Toolbox.ActivateLayoutScenario(layoutScenario);
		
		Toolbox.CalculateEnergy();
		
		Toolbox.Log("Finished energy calculation!", LogLevel.Warn);
		
		// Get results
		Scenario resultsScenario = Workbook.CurrentScenario;
		var subjectWindFarm = resultsScenario.WindFarms.Where(w => w.IsNeighbour == false).FirstOrDefault();
		Toolbox.Log("subject wind farm is: " + subjectWindFarm.Name, LogLevel.Warn);
		
		double netYield = resultsScenario.FarmTotalYields.GetVariantResult("Full").GetValueForFarm(subjectWindFarm).Value / 10e6;	
		string result = string.Format("Net yield for scenario {0}:\t{1} GWh/annum\n", layoutScenario.Name, netYield.ToString("0.##"));
		Toolbox.Log(result, LogLevel.Warn);
		resultString += result;
	}
	Toolbox.Log(resultString);
	Toolbox.Log("END OF SCRIPT", LogLevel.Warn);
}