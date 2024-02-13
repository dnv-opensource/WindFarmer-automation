public void Execute()
{
    try
    {
        // This is a script to demonstrate how you can automate setting up a WFA 
        // project and run flow and energy calculations and export energy results. 

        #region paths and workbook name

		// Edit the following path to show where the input data is stored. 
        string dataPath = @"..\..\..\DemoData\Hawaii";
		// string dataPath = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "Hawaii Inputs");
		
		Toolbox.MeasurementCampaign.SuppressReporting = true;
        
        Toolbox.Log("Scripted energy analysis START", LogLevel.Warn);
        Toolbox.Save();
    
        // We will save a new project with to contain the analysis
        string workbookName = string.Format("Scripted_Energy_Analysis_{0}.wwx", DateTime.Now.ToString("yyMMdd_HHmm"));
        Toolbox.Log("\tSaving the workbook as " + workbookName);
        Toolbox.SaveAs(System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), workbookName));

        #endregion

        #region Import GIS data and set the co-ordinate system

        // Set the site location     
        double lattitude = 20.259495;
        double longitude = -155.866667;
        Location latLonSiteLocation = new Location (longitude, lattitude);
        Toolbox.RedefineSiteLocation(latLonSiteLocation);
    
        // Set the workbook co-ordinate system if it hasn't been set already
        if (Workbook.Geography.Projection == null)
        {
            Toolbox.Log("Setting workbook co-ordinate system");
			// EPSG codes provide a consistent way to define co-ordinate systems and this is what we use in scripting. 
			// Search a reference list like the following to find your co-ordinate system as an ESPG: http://spatialreference.org/ref/epsg/ 
            Projection workbookProjection = Toolbox.GetProjectionFromEpsgCode(32605); 
            Toolbox.RedefineWorkbookProjection(workbookProjection);
        }

        string gisDataPath = System.IO.Path.Combine(dataPath, "GIS data");

        // Import elevation data
        
		Toolbox.Log("Importing elevation data");
        Toolbox.ImportElevationContours(System.IO.Path.Combine(gisDataPath, "Elevation contours - Hawaii.map"), Workbook.Geography.Projection);
        // this .map file has no associated projection information so this must be specified

        Toolbox.ImportElevationGrid(System.IO.Path.Combine(gisDataPath, "SRTM gridded elevations - N20W156.grd"));
        // this .grd elevation grid file has an associated .prj file, "N20W156.prj", descibing the projection 
		// so no projection need be specified, reprojection to the workbook projection is handled automatically on import.
        // Alternatively you can create the elevation grid from the contours already loaded in the workbook:
        // Toolbox.AddElevationGrid( Workbook.Geography.Contours.FirstOrDefault(), 25 );

        Toolbox.Log("Importing background image");
		Toolbox.ImportBackgroundImage( System.IO.Path.Combine( gisDataPath, "Satellite imagery.jpg"  )); // The background is georeferenced with a world file and projection file (.pgw and .prj). A .pgw is needed but you can define the projection from like we did for loading contours
		//	Toolbox.ImportBackgroundImage( System.IO.Path.Combine( gisDataPath, "Background image - Hawaii.png"  )); // alternative full island image, uncomment to load this too

        #endregion

        #region Configure Measurement sites

		// create and add 3 measurement sites to the workbook then set the shear model: 2 masts and 1 reference station
		Mast mast2 = new Mast("M2", new Location(199186, 2242285));
	  	Workbook.Climate.MeasurementSites.Add(mast2);
	  	Toolbox.MeasurementCampaign.SaveShearModel(new UserDefinedShearModel(ShearFittingType.Power, 0.20), mast2);
	  
	    Mast mast3 = new Mast("M3", new Location(202139, 2241811));
	  	Workbook.Climate.MeasurementSites.Add(mast3);
	  	Toolbox.MeasurementCampaign.SaveShearModel(new UserDefinedShearModel(ShearFittingType.Power, 0.21), mast3);
	  
	    ReferenceStation KohalaAirport = new ReferenceStation("Kohala Airport", new Location(201229, 2243339));
	    Workbook.Climate.MeasurementSites.Add(KohalaAirport);
	  	Toolbox.MeasurementCampaign.SaveShearModel(new UserDefinedShearModel(ShearFittingType.Power, 0.22), KohalaAirport);

        // Import time series data in to the workbook for each of the measurement sites
		Toolbox.MeasurementCampaign.LoadData( System.IO.Path.Combine( dataPath, "Time series", "M2 time series.txt"  ), System.IO.Path.Combine( dataPath, "Time series", "M2 time series_LoadSettings.xml" ));
		Toolbox.MeasurementCampaign.LoadData( System.IO.Path.Combine( dataPath, "Time series", "M3 time series.txt"  ), System.IO.Path.Combine( dataPath, "Time series", "M3 time series_LoadSettings.xml" ));
   
        #endregion

        #region Site setup

        // load all turbine types in the folder in to the workbook
        Toolbox.Log("load all turbine types in the folder in to the workbook");

		foreach (string trbxFile in System.IO.Directory.GetFiles( System.IO.Path.Combine( dataPath, "Turbine types"), "*.trbx"))
        {
            TurbineType turbineType = new TurbineType(trbxFile);
            if (Workbook.TurbineTypes.Any(t => t.Name.Equals(turbineType.Name)))
            {
                Toolbox.Log(string.Format("Turbine type {0} already exists in the workbook so we will skip loading {1}", turbineType.Name, trbxFile), LogLevel.Warn);
            }
            else
            {
                Workbook.TurbineTypes.Add(turbineType);
                Toolbox.Log(string.Format("Loaded turbine type {0} from file {1}", turbineType.Name, trbxFile));
            }
        }

        // Create wind farms
        Toolbox.Log("Create Wind farms");

        string myWindFarmName = "My wind farm";
        string neighbourWindFarmName = "Existing Kohala WindFarm";

        Workbook.WindFarms.First().Name = myWindFarmName;

        Workbook.WindFarms.Add(new WindFarm(neighbourWindFarmName));
        Workbook.WindFarms[neighbourWindFarmName].IsNeighbour = true;

        // place turbines

        AddTurbinesFromTabSeparatedFile(System.IO.Path.Combine(dataPath, "Turbines", "My wind farm.txt"), myWindFarmName);
        AddTurbinesFromTabSeparatedFile(System.IO.Path.Combine(dataPath, "Turbines", "Kohala neighbouring wind farm.txt"), neighbourWindFarmName);

        #endregion

        #region Long term wind climate prediction

        // Load time series data in to memory 
        LogAndReport("Load time series data in to memory");

        SpeedTimeSeries M2_ws60S_Mean = Toolbox.MeasurementCampaign.GetTimeSeries<SpeedTimeSeries>("M2~ws60S~Mean");
        SpeedTimeSeries M2_ws60N_Mean = Toolbox.MeasurementCampaign.GetTimeSeries<SpeedTimeSeries>("M2~ws60N~Mean");
        SpeedTimeSeries M2_ws60N_SD = Toolbox.MeasurementCampaign.GetTimeSeries<SpeedTimeSeries>("M2~ws60N~StdDev");
        DirectionTimeSeries M2_wd57_Mean = Toolbox.MeasurementCampaign.GetTimeSeries<DirectionTimeSeries>("M2~wd57~Mean");

        SpeedTimeSeries M3_ws94NW_Mean = Toolbox.MeasurementCampaign.GetTimeSeries<SpeedTimeSeries>("M3~ws94NW~Mean");
        SpeedTimeSeries M3_ws94S_Mean = Toolbox.MeasurementCampaign.GetTimeSeries<SpeedTimeSeries>("M3~ws94S~Mean");
        SpeedTimeSeries M3_ws94S_SD = Toolbox.MeasurementCampaign.GetTimeSeries<SpeedTimeSeries>("M3~ws94S~StdDev");
        DirectionTimeSeries M3_wd94_Mean = Toolbox.MeasurementCampaign.GetTimeSeries<DirectionTimeSeries>("M3~wd94~Mean");

        // Directionaly splice time series at the same height
        LogAndReport("directionaly splice time series at the same height");
        SpeedTimeSeries M2_ws60_DirSplice = Toolbox.MeasurementCampaign.DirectionalSplice(M2_ws60N_Mean, 353, 60, M2_ws60S_Mean, 200, 60, M2_wd57_Mean, 3);
        SpeedTimeSeries M3_ws94_DirSplice = Toolbox.MeasurementCampaign.DirectionalSplice(M3_ws94NW_Mean, 310, 60, M3_ws94S_Mean, 190, 60, M3_wd94_Mean, 3);

        // Save directionally spliced time series results back in to the workbook
        LogAndReport("Save directionally spliced time series results back in to the workbook");
        MeasurementSite M2 = Workbook.Climate.MeasurementSites.Where(m => m.Name == "M2").First();
        MeasurementSite M3 = Workbook.Climate.MeasurementSites.Where(m => m.Name == "M3").First();
        Toolbox.MeasurementCampaign.SaveResultsTimeSeries(M2_ws60_DirSplice, M2, "M2_ws60_DirSplice", true);
        Toolbox.MeasurementCampaign.SaveResultsTimeSeries(M3_ws94_DirSplice, M3, "M3_ws94_DirSplice", true);

        // Reconstruct time series wind speed measurements at M2 from M3
        LogAndReport("Reconstructing time series wind speed measurements at M2 from M3");
        SpeedTimeSeries M2_ws60_synthesisedFromM3 = SynthesiseSpeedTimeSeries(M3_ws94_DirSplice, M3_wd94_Mean, M2_ws60_DirSplice);
        SpeedTimeSeries M2_ws60_reconstructed = Toolbox.MeasurementCampaign.SpliceSeries<SpeedTimeSeries>(M2_ws60_synthesisedFromM3, M2_ws60_DirSplice);
        Toolbox.MeasurementCampaign.SaveResultsTimeSeries(M2_ws60_reconstructed, M2, "M2_ws60_reconstructed", true);

        // Reconstruct time series wind speed measurements at M3 from M2
        LogAndReport("Reconstructing time series wind speed measurements at M3 from M2");
        SpeedTimeSeries M3_ws94_synthesisedFromM2 = SynthesiseSpeedTimeSeries(M2_ws60_DirSplice, M2_wd57_Mean, M3_ws94_DirSplice);
        SpeedTimeSeries M3_ws94_reconstructed = Toolbox.MeasurementCampaign.SpliceSeries<SpeedTimeSeries>(M3_ws94_synthesisedFromM2, M3_ws94_DirSplice);
        Toolbox.MeasurementCampaign.SaveResultsTimeSeries(M3_ws94_reconstructed, M3, "M3_ws94_reconstructed", true);
        
		List<TimeSeries> timeSeriesToExport = new List<TimeSeries>() { M3_ws94_reconstructed, M3_wd94_Mean, M2_ws60_reconstructed, M2_wd57_Mean };
		Toolbox.MeasurementCampaign.ExportTimeSeriesToFile(timeSeriesToExport, "reconstructed time series.tsv");

        // create frequency distributions and compare wind climates at each mast
        LogAndReport("create frequency distributions");
        FrequencyDistribution m2_FD_ws60wd57 = Toolbox.MeasurementCampaign.CreateFrequencyDistribution(M2_ws60_reconstructed, M2_wd57_Mean, true, "m2_FD_ws60wd57");
        FrequencyDistribution m3_FD_ws94wd94 = Toolbox.MeasurementCampaign.CreateFrequencyDistribution(M3_ws94_reconstructed, M2_wd57_Mean, true, "m3_FD_ws94wd94");

        LogAndReport("\t comparing FDs on Masts M2 and M3...");
        Toolbox.MeasurementCampaign.CompareFrequencyDistribution(m2_FD_ws60wd57, m3_FD_ws94wd94, Workbook.TurbineTypes.First().NormalPerformanceTables.First());

        LogAndReport("create turbulence intensity distributions");
        TurbulenceIntensityDistribution M2_60m_TI = Toolbox.MeasurementCampaign.CreateTurbulenceIntensityDistribution(M2_ws60_reconstructed, M2_ws60N_SD, M2_wd57_Mean, "M2_60m_TI");
        TurbulenceIntensityDistribution M3_94m_TI = Toolbox.MeasurementCampaign.CreateTurbulenceIntensityDistribution(M3_ws94_reconstructed, M3_ws94S_SD, M3_wd94_Mean, "M3_94m_TI");

		LogAndReport("Save frequency distributions and turbulence intensity distributions back to the workbook as inputs to WAsP and energy calculations");
		Toolbox.MeasurementCampaign.SaveDistribution(Workbook.Climate.MeasurementSites["M2"], m2_FD_ws60wd57, m2_FD_ws60wd57.Name, 60,true);
		Toolbox.MeasurementCampaign.SaveDistribution(Workbook.Climate.MeasurementSites["M2"], M2_60m_TI, M2_60m_TI.Name, 60,true);
		Toolbox.MeasurementCampaign.SaveDistribution(Workbook.Climate.MeasurementSites["M3"], m3_FD_ws94wd94, m3_FD_ws94wd94.Name, 94,true);
		Toolbox.MeasurementCampaign.SaveDistribution(Workbook.Climate.MeasurementSites["M3"], M3_94m_TI, M3_94m_TI.Name, 94,true);

		Toolbox.Log("Export frequency distributions to file");
        Toolbox.MeasurementCampaign.ExportFrequencyDistribution(m2_FD_ws60wd57, string.Format("{0}.tab", m2_FD_ws60wd57.Name));
        Toolbox.MeasurementCampaign.ExportFrequencyDistribution(m3_FD_ws94wd94, string.Format("{0}.tab", m3_FD_ws94wd94.Name));
        Toolbox.MeasurementCampaign.ExportTurbulenceIntensityDistribution(M2_60m_TI, string.Format("{0}.wti", M2_60m_TI.Name));
        Toolbox.MeasurementCampaign.ExportTurbulenceIntensityDistribution(M3_94m_TI, string.Format("{0}.wti", M3_94m_TI.Name));

        Toolbox.Log("Wind analysis complete", LogLevel.Warn);

        #endregion

        #region Flow model

        Toolbox.Log("Begin wind flow modelling", LogLevel.Warn);

        Toolbox.Log("\t creating initiation regions");

        List<IReadable2DLocation> initiationRegion1Locations = GetListOfLocationsFromTabSeparatedTextFile(System.IO.Path.Combine(dataPath, "GIS data", "Initiation region 1.txt"));
        Workbook.Climate.InitiationRegions.Add(new InitiationRegion("initiated from M2", initiationRegion1Locations, mast2));

        List<IReadable2DLocation> initiationRegion2Locations = GetListOfLocationsFromTabSeparatedTextFile(System.IO.Path.Combine(dataPath, "GIS data", "Initiation region 2.txt"));
        Workbook.Climate.InitiationRegions.Add(new InitiationRegion("initiated from M3", initiationRegion2Locations, mast3));

        if (Toolbox.IsWaspAvailable(WAsPVersion.Version12) == WAsPStatus.Available)
        {
            Toolbox.Log("\t running WAsP 12 flow model");
            Workbook.ModelSettings.FlowSettings.FlowModelType = FlowModelType.WaspFromFreqDist;
            Workbook.ModelSettings.FlowSettings.WAsPParameters.WAsPVersion = WAsPVersion.Version11;
        }
        else
        {
            Toolbox.Log("\t running simple flow model");
            Workbook.ModelSettings.FlowSettings.FlowModelType = FlowModelType.Simple;        
        }

        Toolbox.CalculateWindFlow();
        Toolbox.Log("Completed wind flow calculation", LogLevel.Warn);

        #endregion

        #region Annual Energy and wake calculation

        Toolbox.Log("Starting Wake and energy calculation", LogLevel.Warn);

        Scenario annualEnergyAndWakeResults = Toolbox.CalculateEnergy();

        double annualEnergyProduction = annualEnergyAndWakeResults.FarmTotalYields["Full"].Result.GetValueForFarm(annualEnergyAndWakeResults.WindFarms.Where(w => w.Name == myWindFarmName).First()) / 1000000;
		Toolbox.Log( string.Format("Scripted energy analysis COMPLETE \r\r \t Full AEP for {0} is {1} GWh/Annum", myWindFarmName, annualEnergyProduction.ToString("0.0")), LogLevel.Warn);	
		

        #endregion

	Toolbox.Save();
    }
    catch(Exception e)
    {
        Toolbox.Log(e.StackTrace);
        if (!String.IsNullOrEmpty(Toolbox.CurrentWorkbookPath))
        {
            string exceptionTraceFilePath = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(Toolbox.CurrentWorkbookPath), "ExceptionStackTrace.txt");
            using (System.IO.StreamWriter file = new System.IO.StreamWriter(exceptionTraceFilePath))
            {
                file.WriteLine(e.Message);
                file.WriteLine(e.StackTrace);
            }
        }
        throw;
    }
}


#region helper Functions

	public void LogAndReport(string logAndReportString)
	{
		Toolbox.Log("\t" + logAndReportString);
		Toolbox.MeasurementCampaign.InsertComment(logAndReportString);
	}

	public SpeedTimeSeries SynthesiseSpeedTimeSeries(SpeedTimeSeries referenceSpeedTS, DirectionTimeSeries referenceDirectionTS, SpeedTimeSeries siteSpeedTS, int numberOfDirections = 12)
	{
		CorrelationResult correlationResult =	Toolbox.MeasurementCampaign.Correlate(referenceSpeedTS, referenceDirectionTS, siteSpeedTS, referenceDirectionTS, 3, -1, true, numberOfDirections);
		
		return Toolbox.MeasurementCampaign.SpeedUpSeries(referenceSpeedTS, referenceDirectionTS, correlationResult.SpeedTrend  );
	}

	public void AddTurbinesFromTabSeparatedFile( string filePath, string windFarmName)
	{
		List<List<string>> turbinePropertyListOfLists= ParseTabSeparatedTextFile(System.IO.Path.Combine( filePath), 0);
		
		foreach ( List<string> turbinePropertyList in turbinePropertyListOfLists)
		{
			double easting = double.Parse( turbinePropertyList[1]);
			double northing = double.Parse( turbinePropertyList[2]);
			Workbook.WindFarms[windFarmName].Turbines.Add(new Turbine(turbinePropertyList[0], new Location(easting, northing),Workbook.TurbineTypes[turbinePropertyList[4]]));
		}

	}

	List<IReadable2DLocation> GetListOfLocationsFromTabSeparatedTextFile (string filePath)
	{
		List<List<string>> initiationRegion1ListOfLocations = ParseTabSeparatedTextFile(filePath ,0);
		
		List<IReadable2DLocation> initiationRegionPoints = new List<IReadable2DLocation>();
		foreach (var initiationRegionPoint in initiationRegion1ListOfLocations)
		{
			initiationRegionPoints.Add(new Location(double.Parse(initiationRegionPoint[0]),double.Parse(initiationRegionPoint[1])));
		}
		return initiationRegionPoints;
	}

	public List<List<string>> ParseTabSeparatedTextFile(string filePath, int numberOfHeaderLines)
	{
		Toolbox.Log(string.Format("Reading Time Series File {0}", filePath));
		if (!System.IO.File.Exists(filePath))
		{
			Toolbox.Log("...File Could not be found. Exiting.", LogLevel.Error);
			return null;
		}

		List<List<string>> parsedTextFileListOfLists = new List<List<string>>();
		
		using (System.IO.StreamReader reader = new System.IO.StreamReader(filePath))
		{		
			// Header lines not processed
			for (int i = 0; i < numberOfHeaderLines; i++)
			{
				reader.ReadLine();
			}
			string line;
			while((line = reader.ReadLine()) != null)
			{			
				parsedTextFileListOfLists.Add( line.Split('\t').ToList());
			}
		}
		return parsedTextFileListOfLists;
	}

#endregion