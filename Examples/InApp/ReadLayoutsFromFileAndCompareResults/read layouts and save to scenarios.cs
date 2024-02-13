/// <Summary>
/// The main entry point of the script.
/// </Summary>
public void Execute()
{
	try{
			string layoutsPath =  Path.Combine(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "Layouts");	
		string[] layoutDirectories = Directory.GetDirectories(layoutsPath);
		
		// Set energy settings
		Workbook.ModelSettings.EnergySettings.CalculateEfficiencies = true;
		
		
		// Wind farm results setup
		string windFarmTemplateExcelPath = Path.Combine(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "Template sheet.xlsx");
        string windFarmResultsFilePath = Path.Combine(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "Results_FarmComparisson.xlsx");
		File.Copy(windFarmTemplateExcelPath, windFarmResultsFilePath, true);
		List<string> windFarmResultsToExcel = new List<string>() {
			"Wind Farm Name","Turbine Type", "Hub Height", "Gross Yield [MWh/Annum]", "Full Yield [MWh/Annum] (excludes blockage)", "Hysteresis efficiency [%]", "Internal wake efficiency [%]", "External wake efficiency [%]", "WSM efficiency [%]", "Blockage efficiency [%]"  };
		int numberOfWindFarms = 0;
		
		foreach ( string layoutDir in layoutDirectories  )
		{
			string windFarmName = Path.GetFileNameWithoutExtension(layoutDir);
			Toolbox.Log("wind farm name: " + windFarmName );

			if( Workbook.LayoutScenarios[windFarmName] != null)
			{
				Toolbox.DeleteLayoutScenario(Workbook.LayoutScenarios[windFarmName]);
			}
			
			// Clone the default scenario, and name it the wind farm to import. This allows you to set up wind farms in the existing scenario
			Toolbox.CloneLayoutScenario(Workbook.LayoutScenarios["Layout design one"], windFarmName, true);
			
			if( Workbook.WindFarms[windFarmName] != null)
			{
				Workbook.WindFarms.Remove(windFarmName);
			}
			
			WindFarm thisLayoutWindFarm = new WindFarm( windFarmName );
			Workbook.WindFarms.Add( thisLayoutWindFarm );
			numberOfWindFarms ++;
			
			#region load turbine types
			//load any turbine types in the workbook in to workbook 
			DirectoryInfo layoutPath = new DirectoryInfo(layoutDir);
			FileInfo turbineTypeFile = layoutPath.GetFiles("*.trbx").First();
			
			TurbineType loadType = new TurbineType(turbineTypeFile.FullName);
			if( Workbook.TurbineTypes.Any( x => x.Name == loadType.Name ))
			{
				Workbook.TurbineTypes.Remove(loadType.Name);
				Workbook.TurbineTypes.Add(loadType);
				Toolbox.Log(string.Format("Replaced existing turbine type {0} with turbine type from file with same name: ", loadType.Name));
			}
			else
			{
				Workbook.TurbineTypes.Add(loadType);
				Toolbox.Log("Loaded turbine type: " + loadType.Name);
			}		
			#endregion
			
			#region load turbine locations in to a new wind farm
			//load any turbine types in the workbook in to workbook 
			FileInfo locationsListFile = layoutPath.GetFiles("*.txt").First();
			
			// Read All lines in file into array of strings
			string[] linesInFile = System.IO.File.ReadAllLines(locationsListFile.FullName);
			// Use a loop to parse each line
			foreach(string line in linesInFile)
			{
				// split by the tab character to get the several items in each line
				// Expecting 5 items per line (name, x and y coordinates, wind farm name and turbine type name
				string[] items = line.Split('\t');
				
				if(items.Count() < 3) continue;
					
				// Indexes are 0-based
				string turbineName = items[0];
				string xCoordinate = items[1];
				string yCoordinate = items[2];
				
				// Create a location object with the given coordinates, string needs to be converted into double type
				Location turbineLocation = new Location(Convert.ToDouble(xCoordinate), Convert.ToDouble(yCoordinate));
				// Create the turbine object
				Turbine turbine = new Turbine(turbineName, turbineLocation, loadType);
				// Add the turbine to a wind farm thus to the workbook

				thisLayoutWindFarm.Turbines.Add(turbine);		
				Toolbox.Log("Added Turbine " + turbineName + " to wind farm " + thisLayoutWindFarm.Name);
			} 	
			
			#endregion
			
			#region calculate flow and energy
			
			
			// Re-run the flow model to calculate at the new hub height
	        Toolbox.CalculateWindFlow();

	        // Calculate the energy yeild
	        Scenario results = Toolbox.CalculateEnergy();
			
			#endregion
			
			
			#region Report results
			
	        ReadOnlyWindFarm rWindFarm = results.WindFarms.Where(wf => wf.Name.Equals(windFarmName)).First();

			#region wind farm results
			
			windFarmResultsToExcel.Add( rWindFarm.Name);
			windFarmResultsToExcel.Add( loadType.Name );
			windFarmResultsToExcel.Add( loadType.Height.ToString());
			windFarmResultsToExcel.Add( ( results.FarmTotalYields.GetVariantResult("Gross").GetValueForFarm( rWindFarm ) / 1000 ).ToString());
			windFarmResultsToExcel.Add( ( results.FarmTotalYields.GetVariantResult("Full").GetValueForFarm( rWindFarm ) / 1000 ).ToString());
			windFarmResultsToExcel.Add( results.Efficiencies.HysteresisEfficiency.GetValueForFarm( rWindFarm ).ToString());
			windFarmResultsToExcel.Add( results.Efficiencies.InternalWakeEfficiency.GetValueForFarm( rWindFarm ).ToString());
			windFarmResultsToExcel.Add( results.Efficiencies.WakeFromNeighboursEfficiency.GetValueForFarm( rWindFarm ).ToString());
			windFarmResultsToExcel.Add( results.Efficiencies.WindSectorManagementEfficiency.GetValueForFarm( rWindFarm ).ToString());
			windFarmResultsToExcel.Add( results.Efficiencies.BlockageCorrection.ToString());
		
			#endregion
			
			List<string> resultsToExcel = new List<string>() {"Turbine Name","Turbine Type", "Hub Height", "Gross Yield", "Full Yield" };
			int numberOfTurbines = 0;

	        foreach (ReadOnlyTurbine turb in rWindFarm.Turbines)
	        {
	            // Gross Yield
	            Yield grossYield = results.TurbineTotalYields.GetVariantResult("Gross").GetValueForTurbine(turb);
	            // Full yield of the turbine
	            Yield fullYield = results.TurbineTotalYields.GetVariantResult("Full").GetValueForTurbine(turb);

				
	            Toolbox.Log("Results " + turb.Name + ": Gross: " + grossYield.ToString() + " Full: " + fullYield.ToString());
	            resultsToExcel.Add(turb.Name);
				resultsToExcel.Add(turb.TurbineType.Name);
				resultsToExcel.Add(turb.TurbineType.HubHeight.ToString());
	            resultsToExcel.Add(grossYield.ToString());
	            resultsToExcel.Add(fullYield.ToString());
	            numberOfTurbines = numberOfTurbines + 1;
	        }

	        // Export to excel
			string templateExcelPath = Path.Combine(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "Template sheet.xlsx");
	        string resultsFilePath = Path.Combine(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "Results_" + thisLayoutWindFarm.Name + ".xlsx");
	        string sheetName = "Results";
			string rangeName = "A1:E" + (numberOfTurbines + 1).ToString();

			File.Copy(templateExcelPath, resultsFilePath, true);
			Toolbox.WriteRangeToExcel(resultsFilePath, sheetName, rangeName, resultsToExcel);
			
			Toolbox.Log( "Written turbine results for wind farm " + thisLayoutWindFarm.Name); 

			#endregion
			
			thisLayoutWindFarm.ExcludeFromCalculation = true;
		}
	
	    // Export wind farm results to excel
		Toolbox.WriteRangeToExcel(windFarmResultsFilePath, "Results", "A1:J" + (numberOfWindFarms + 1).ToString(), windFarmResultsToExcel);			
		Process.Start(windFarmResultsFilePath);
		
		Toolbox.Log( "Multi-layout comparisson complete");
	}
	catch (Exception e)
	{
		Toolbox.Log(e.Message);
		Toolbox.Log(e.StackTrace);
		throw;
	}
	
}