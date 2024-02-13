/// <summary>
///  (Made-up) background story & assumptions: 
///  The turbine spacing has been fixed to roughly 10x6D prior to this layout design exercise 
/// 	- a result of the array cable cost considerations, as well as environmental & fishery impacts.
///  The grid connection capacity is limited to 800MW, or fifty 19MW turbines.
///  Given the above assumptions the lease area seems to be too big, so the the layout designer is tasked with identifying 
///  the best sub-region with the lease area and then to designing a first-cut gridded layout.
///  This need to be done with consideration given to variations in wind resource, bathymetry and external wake impacts across the site,
///  as well as exclusion zone (wrecks, connection cable corridor, etc).
/// 
///  This script encodes a simple exploration of the possible solution space. 
///  It's primarily a demonstration of WindFarmer's automation capabilities and should not be regarded as
///  a complete approach to offshore layout design. 
/// 
///  Notes on model settings: 
///  To speed up execution, coarser directional resolution is used in the 'optimisation' step.
///  Since the distance to neighbouring farms will change across scenarios, the cluster wake impacts are believed to contribute to the (simplistic) cost-benefit function. 
///  WindFarmer's implementation of Orsted's TurbOPark model does not yet contain the RHBW blockage model component, makign it unsuitable for assessing internal wakes.
///  However it is believed to give sensible results when it comes to farm-on-farm wake interactions. Therefore TurbOPark is used in the north-south optimisation step.
///  Once a promising layout is identified, calculation resolution is increased and DNV typical turbine interaction modeling (EV + LWF + BEET) is used to evaluate the 
///  the final yield estimate. 
/// </summary>
/// 

public void Execute()
{
	Toolbox.ActivateLayoutScenario(Workbook.LayoutScenarios["Best variant"]);
	// initial turbine separation settings
	Workbook.ModelSettings.LayoutOptimisationSettings.TurbineConstraints.TurbineSeparationDistanceConstraints.UseCircular = false;
	Workbook.ModelSettings.LayoutOptimisationSettings.TurbineConstraints.TurbineSeparationDistanceConstraints.EllipticalBearingOfLongAxis = 250;
	Workbook.ModelSettings.LayoutOptimisationSettings.TurbineConstraints.TurbineSeparationDistanceConstraints.EllipticalLongAxisInDiameters = 10;
	Workbook.ModelSettings.LayoutOptimisationSettings.TurbineConstraints.TurbineSeparationDistanceConstraints.EllipticalShortAxisInDiameters = 6;
	bool excludeNeighboursInOptimization = true;
	// resolution of the simple search
	int noSteps = 20;
	// farm size
	int targetTurbineCount = 50;
	// explore layout variants along the north-south axis
	int bestI = this.ExploreNorthSouth(targetTurbineCount, noSteps, 0, excludeNeighboursInOptimization);
	// for the best north-south choice explore ellipse axis bearing options around the dominating wind dir
	int bestJ = this.ExploreAxisBearing(targetTurbineCount, noSteps, bestI, excludeNeighboursInOptimization);
	// Apply the best layout to the workbbok and calculate yield
	GenerateLayoutOnDemoSite(bestI, bestJ, targetTurbineCount);
	this.SetDetailedModelingSettings();
	Toolbox.CalculateEnergy();
	Toolbox.RunMonteCarloEnergyAnalysis();
}

public int ExploreNorthSouth(int targetTurbineCount, int noSteps, int fixJ, bool excludeNeighbours)
{
	// the function moves the layout to gradually to the south, redesigns it at each step and estimates the cost-benefit fucntion at each point returning the best variant
	Dictionary<int, Tuple<double, double>> searchResults = new Dictionary<int, Tuple<double, double>>();
	Dictionary<int, double> costBenefitScore = new Dictionary<int, double>();
	Scenario scenario;
	double meanDepth, fullYield;
	int turbineCount;
	this.SetCoarseModelingSettingsForNorthSouthExploration(excludeNeighbours);
	StreamWriter outputFile = new StreamWriter(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath)+"\\south-north-exploration.txt");
	string logMessage;
	foreach (int i in Enumerable.Range(0, noSteps))
	{
		this.GenerateLayoutOnDemoSite(i, fixJ, targetTurbineCount);
		turbineCount = Workbook.WindFarms["OffshoreDemoSite"].Turbines.Count();
		if (turbineCount == targetTurbineCount)
		{
			meanDepth = Math.Abs(Workbook.WindFarms["OffshoreDemoSite"].Turbines.Select(t => Toolbox.GetElevation(t.Location).Value).Average());
			scenario = Toolbox.CalculateEnergy();
			fullYield = scenario.FarmTotalYields.GetVariantResult("Full").GetValueForFarm(scenario.WindFarms.Where(f => f.Name == "OffshoreDemoSite").First());
			searchResults[i] = new Tuple<double, double>(meanDepth, fullYield);
			costBenefitScore[i] = this.GetCostBenefitEstimate(searchResults[i].Item2, searchResults[i].Item1, searchResults[0].Item2, searchResults[0].Item1);
			logMessage = "i: " + i.ToString() +
						"   DEPTH:" + searchResults[i].Item1.ToString() +
						"   YIELD:" + searchResults[i].Item2.ToString() +
						"   COST-BENEFIT-SCORE:" + costBenefitScore[i].ToString();
			outputFile.WriteLine(logMessage);
			Toolbox.Log(logMessage);
		}
	}
	outputFile.Close();
	double bestScore = costBenefitScore.Max(kv => kv.Value);
	return costBenefitScore.Where( kv => kv.Value == bestScore).First().Key;	
}

public int ExploreAxisBearing(int targetTurbineCount, int noSteps, int fixedI, bool excludeNeighbours)
{
	// the function rotates the separation ellipses in the packed layout in search of the best setting
	Dictionary<int, double> searchResults = new Dictionary<int, double>();
	Scenario scenario;
	double fullYield;
	int turbineCount;
	this.SetCoarseModelingSettingsForAxisBearingExploration(excludeNeighbours);
	StreamWriter outputFile = new StreamWriter(Path.GetDirectoryName(Toolbox.CurrentWorkbookPath)+"\\axis-bearing-exploration.txt");
	string logMessage;
	foreach (int j in Enumerable.Range(0, noSteps))
	{
		this.GenerateLayoutOnDemoSite(fixedI, j, targetTurbineCount);
		turbineCount = Workbook.WindFarms["OffshoreDemoSite"].Turbines.Count();
		if (turbineCount == targetTurbineCount)
		{
			scenario = Toolbox.CalculateEnergy();
			fullYield = scenario.FarmTotalYields.GetVariantResult("Full").GetValueForFarm(scenario.WindFarms.Where(f => f.Name == "OffshoreDemoSite").First());
			searchResults[j] = fullYield;
			logMessage = "j: " + j.ToString() + 
						"   YIELD:" + fullYield.ToString();
			outputFile.WriteLine(logMessage);
			Toolbox.Log(logMessage);
		}
	}
	outputFile.Close();
	double bestYield= searchResults.Max(e => e.Value);
	return searchResults.Where(e => e.Value == bestYield).First().Key;	
}

public double GetCostBenefitEstimate(double yield, double meanDepth, double baselineYield, double baselineDepth)
{
	return yield / baselineYield + (1 - meanDepth / baselineDepth) / 3;
}

public void GenerateLayoutOnDemoSite(int i, int j, int targetTurbineCount)
{
			int startingPointEasting = 360000;
			int startingPointNorthing = 5936000;
			int verticalTranslationStepSize = 1000; // there's by default 20 steps and the site spans approx. 20km north-south
			int axisBearingSearchStartingPointDeg = 240; 
			int axisBearingSearchStepSizeDeg = 2; // with the defualt 20 steps this translates to 40 deg. search range, roughly aroung the dominating wind dir.
			Location startLocation = new Location(startingPointEasting, startingPointNorthing - i * verticalTranslationStepSize);
			Workbook.ModelSettings.LayoutOptimisationSettings.TurbineConstraints.TurbineSeparationDistanceConstraints.EllipticalBearingOfLongAxis = 
				axisBearingSearchStartingPointDeg  + j * axisBearingSearchStepSizeDeg;
			Workbook.WindFarms["OffshoreDemoSite"].Turbines.Clear();
			Toolbox.GenerateClosePackedLayout(
				Workbook.WindFarms["OffshoreDemoSite"], 
				Workbook.TurbineTypes["Bladed Concept Model 19-MW 265-D Offshore"],
				targetTurbineCount,
				startLocation,
				true);
}

public void SetCoarseModelingSettingsForNorthSouthExploration(bool excludeNeighbours){
	Workbook.ModelSettings.EnergySettings.WakeModelType = WakeModelType.TurbOPark;
	Workbook.ModelSettings.EnergySettings.ApplyLargeWindFarmCorrection = false;
	Workbook.ModelSettings.EnergySettings.CalculateBlockageEfficiency = false;
	Workbook.ModelSettings.EnergySettings.CalculateEfficiencies = false;
	Workbook.ModelSettings.EnergySettings.UseAssociationMethod = true;
	Workbook.ModelSettings.EnergySettings.MaximumWindSpeedForCalculation = 30;
	Workbook.ModelSettings.EnergySettings.NumberOfDirectionSectors = 72;
	Workbook.ModelSettings.EnergySettings.ApplyHysteresisAdjustment = false;
	foreach (WindFarm wf in Workbook.WindFarms)
	{
		if (wf.IsNeighbour)
		{
			wf.ExcludeFromCalculation = !excludeNeighbours;
		}
	}
}

public void SetCoarseModelingSettingsForAxisBearingExploration(bool excludeNeighbours){
	Workbook.ModelSettings.EnergySettings.WakeModelType = WakeModelType.EddyViscosity;
	Workbook.ModelSettings.EnergySettings.ApplyLargeWindFarmCorrection = true;
	Workbook.ModelSettings.EnergySettings.CalculateBlockageEfficiency = false;
	Workbook.ModelSettings.EnergySettings.CalculateEfficiencies = false;
	Workbook.ModelSettings.EnergySettings.UseAssociationMethod = true;
	Workbook.ModelSettings.EnergySettings.MaximumWindSpeedForCalculation = 30;
	Workbook.ModelSettings.EnergySettings.NumberOfDirectionSectors = 180;
	Workbook.ModelSettings.EnergySettings.ApplyHysteresisAdjustment = false;
	foreach (WindFarm wf in Workbook.WindFarms)
	{
		if (wf.IsNeighbour)
		{
			wf.ExcludeFromCalculation = excludeNeighbours;
		}
	}
}

public void SetDetailedModelingSettings(){
	Workbook.ModelSettings.EnergySettings.WakeModelType = WakeModelType.EddyViscosity;
	Workbook.ModelSettings.EnergySettings.ApplyLargeWindFarmCorrection = true;
	Workbook.ModelSettings.EnergySettings.LargeWindFarmCorrectionSettings.BaseRoughness = 0.0002;
	Workbook.ModelSettings.EnergySettings.LargeWindFarmCorrectionSettings.IncreasedRoughness = 0.192;
	Workbook.ModelSettings.EnergySettings.LargeWindFarmCorrectionSettings.DistanceInDiametersToStartOfRecovery = 120;
	Workbook.ModelSettings.EnergySettings.LargeWindFarmCorrectionSettings.DistanceInDiametersFromStartOfRecoveryToHalfRecovery = 60;
	Workbook.ModelSettings.EnergySettings.CalculateBlockageEfficiency = true;
	Workbook.ModelSettings.EnergySettings.CalculateEfficiencies = true;
	Workbook.ModelSettings.EnergySettings.UseAssociationMethod = true;
	Workbook.ModelSettings.EnergySettings.MaximumWindSpeedForCalculation = 70;
	Workbook.ModelSettings.EnergySettings.NumberOfDirectionSectors = 180;
	Workbook.ModelSettings.EnergySettings.ApplyHysteresisAdjustment = true;
	foreach (WindFarm wf in Workbook.WindFarms)
	{
		if (wf.IsNeighbour)
		{
			wf.ExcludeFromCalculation = false;
		}
	}
}