/// <Summary>
/// Script to export a google earth KMZ to let you visualise your wind farm layout.
/// </Summary>
public void Execute()
{
	try
	{	
		#region Settings
		// Verify that workbook is not temporary	
		string currentWorkingDir = string.Empty;
		if (!string.IsNullOrEmpty(Toolbox.CurrentWorkbookPath))
		{
			currentWorkingDir = System.IO.Path.GetDirectoryName(Toolbox.CurrentWorkbookPath);
		}
		else
		{
			Toolbox.Log("Workbook is temporary, needs to be saved before running this script. Exiting.", LogLevel.Error);
			return;
		}
		
		// Setup paths to support data
		string commonAnalystFolder = @"C:\Users\Public\Documents\WindFarmer - Analyst Common\Scripts";
		string supportDataFolderName = "ExportToKmz";
		if (!System.IO.Directory.Exists(System.IO.Path.Combine(commonAnalystFolder, supportDataFolderName)))
		{
			Toolbox.Log("A folder named ExportToKmz inside the Common scripts folder was expected. This folder should contain the support data to this script. Exiting.", LogLevel.Error);
			return;
		}
		
		string pathWindRoseTemplate = System.IO.Path.Combine(commonAnalystFolder, supportDataFolderName, "windRoseTemplate.kml");
		string pathWindRoseBlank = System.IO.Path.Combine(commonAnalystFolder, supportDataFolderName, "windRoseBlank.kml");
		string pathTurbineModel = System.IO.Path.Combine(commonAnalystFolder, supportDataFolderName, "windmill-1.dae");
		string outputFileName = "ProjectExported"; // No extension
		
		if (!System.IO.File.Exists(pathWindRoseTemplate) ||
			!System.IO.File.Exists(pathWindRoseBlank) || 
			!System.IO.File.Exists(pathTurbineModel))
		{
			Toolbox.Log(string.Format(@"Expected support data files were not found. Please check that windRoseTemplate.kml, windRoseBlank.kml, windmill-1.dae exist in {0}", 
				System.IO.Path.Combine(commonAnalystFolder, supportDataFolderName)), LogLevel.Error);
			return;
		}
		#endregion
		
		// Template KML
		XmlDocument template = new XmlDocument();
		template.Load(pathWindRoseTemplate);

		// Output KML
		XmlDocument doc = new XmlDocument();
		doc.Load(pathWindRoseBlank);

		XmlNamespaceManager xnm = new XmlNamespaceManager(new NameTable());
		xnm.AddNamespace("kml","http://www.opengis.net/kml/2.2");
		XmlNode docElement = doc.SelectSingleNode("/kml:kml/kml:Document", xnm);

		//WGS84 projection
		var geoProjection = Toolbox.GetProjectionFromEpsgCode(4326);

		// Center of Project
		Location centreOfProject = getCentreOfProject();
		Location centreOfProjectLonLat = (Location)Toolbox.ReprojectPoint(centreOfProject, Workbook.Geography.Projection, geoProjection);
		
		XmlNode lookAtNode = doc.CreateNode(XmlNodeType.Element, "LookAt", "http://www.opengis.net/kml/2.2");
		XmlNode lookAtLatitude = doc.CreateNode(XmlNodeType.Element, "latitude", "http://www.opengis.net/kml/2.2");
		lookAtLatitude.InnerText = centreOfProjectLonLat.Y.ToString();
		lookAtNode.AppendChild(lookAtLatitude);
		
		XmlNode lookAtLongitude = doc.CreateNode(XmlNodeType.Element, "longitude", "http://www.opengis.net/kml/2.2");
		lookAtLongitude.InnerText = centreOfProjectLonLat.X.ToString();
		lookAtNode.AppendChild(lookAtLongitude);
			
		XmlNode lookAtRange = doc.CreateNode(XmlNodeType.Element, "range", "http://www.opengis.net/kml/2.2");
		lookAtRange.InnerText = "10000.0";
		lookAtNode.AppendChild(lookAtRange);
		
		XmlNode lookAtTilt = doc.CreateNode(XmlNodeType.Element, "tilt", "http://www.opengis.net/kml/2.2");
		lookAtTilt.InnerText = "45.0";
		lookAtNode.AppendChild(lookAtTilt);
		docElement.AppendChild(lookAtNode);
		
		// Masts
		XmlNode mastsFolder = doc.CreateNode(XmlNodeType.Element, "Folder", "http://www.opengis.net/kml/2.2");
		docElement.AppendChild(mastsFolder);
		XmlNode name = doc.CreateNode(XmlNodeType.Element, "name", "http://www.opengis.net/kml/2.2");
		name.InnerText = "Masts";
		mastsFolder.AppendChild(name);

		foreach (var mast in Workbook.Climate.MeasurementSites){
			LogAsInfo(String.Format("Adding Mast {0}", mast.Name));
			XmlNode mastFolderNode = template.SelectSingleNode("/kml:kml/kml:Document/kml:Folder/kml:Folder[1]", xnm);
			mastFolderNode["name"].InnerText = mast.Name;		

			// Select the highest wind climate
			WindClimate windClimate = mast.WindClimates.OrderByDescending(wc => wc.HeightAboveGroundLevel).FirstOrDefault();
			
			Location geoMast = (Location)Toolbox.ReprojectPoint(mast.Location, Workbook.Geography.Projection, geoProjection);			
			double mastLatitude = geoMast.Y;
			double mastLongitude = geoMast.X;
			
			XmlNode windRoseNode = mastFolderNode["Placemark"];
			XmlNode mastNode = mastFolderNode["Placemark"].NextSibling;
					
			// Change Properties of Mast placemark
			int indexOfExtension = mast.Name.LastIndexOf(".");
			if (indexOfExtension >= 0){
				mastNode["name"].InnerText = mast.Name.Substring(0, indexOfExtension);
			}else{
				mastNode["name"].InnerText = mast.Name;
			}
			
			double windClimateHeightAboveGround = 100;
			
			if(windClimate!= null)
			{
				windClimateHeightAboveGround = windClimate.HeightAboveGroundLevel;
			}
			
			mastNode["Point"]["coordinates"].InnerText = String.Format("{0},{1},{2}", 
					mastLongitude,
					mastLatitude,
					windClimateHeightAboveGround);
			
			// Change Properties of Wind Rose placemark	
			windRoseNode["name"].InnerText = mast.Name;		
			windRoseNode["Point"]["coordinates"].InnerText = String.Format("{0},{1},{2}",
					mastLongitude,
					mastLatitude,
					windClimateHeightAboveGround);
			

//			 Function that calculates a triangle in geographic coordinates representing a direction sector 
//			  scaled by the sector probabilities 
			if( windClimate != null )		
			{
				if( windClimate.FrequencyDistribution != null )
				{
					string fdName = string.Format("{0}~{1}", mast.Name, windClimate.FrequencyDistribution.Name);
					
					FrequencyDistribution fd = Toolbox.MeasurementCampaign.GetFrequencyDistribution(  fdName );
					
					if (fd != null)
					{
						string polygonCoordinates = "";
					
						double binSize= 360.0/Convert.ToDouble(fd.NumberOfDirectionSectors);
						for (int i = 0; i < fd.NumberOfDirectionSectors; i++)
						{
							double binCenter = 0.0 + Convert.ToDouble(i)*binSize;
							double sectorProbability = fd.ByDirectionFrequencies[i] *100;
							polygonCoordinates += TriangleBasedOnSectorProbabilities(mastLongitude, 
																					mastLatitude, 
																					fd.HeightAboveGround,
																					binCenter,
																					binSize,
																					sectorProbability);
						}
					
						//Close Polygon
						polygonCoordinates += String.Format("{0},{1},{2}", mastLongitude, mastLatitude, fd.HeightAboveGround);	
						windRoseNode["Polygon"]["outerBoundaryIs"]["LinearRing"]["coordinates"].InnerText = polygonCoordinates;
					}
				}
			}
			
			mastsFolder.AppendChild(doc.ImportNode(mastFolderNode, true));
		}//masts

		XmlNode windFarmsFolder = doc.CreateNode(XmlNodeType.Element, "Folder", "http://www.opengis.net/kml/2.2");
		docElement.AppendChild(windFarmsFolder);
		XmlNode windFarmsFolderName = doc.CreateNode(XmlNodeType.Element, "name", "http://www.opengis.net/kml/2.2");
		windFarmsFolderName.InnerText = "Wind Farms";
		windFarmsFolder.AppendChild(windFarmsFolderName);
		
		// Wind Farms
		foreach (WindFarm WindFarm in Workbook.WindFarms){	
		
			XmlNode projectFolder = doc.CreateNode(XmlNodeType.Element, "Folder", "http://www.opengis.net/kml/2.2");
			windFarmsFolder.AppendChild(projectFolder);
			XmlNode windFarmName = doc.CreateNode(XmlNodeType.Element, "name", "http://www.opengis.net/kml/2.2");
			windFarmName.InnerText = WindFarm.Name;
			projectFolder.AppendChild(windFarmName);
		
			// Create Folder For Turbines in Output KML
			XmlNode folderTurbines = doc.CreateNode(XmlNodeType.Element, "Folder", "http://www.opengis.net/kml/2.2");	
			projectFolder.AppendChild(folderTurbines);
			XmlNode folderTurbinesName = doc.CreateNode(XmlNodeType.Element, "name", "http://www.opengis.net/kml/2.2");
			folderTurbinesName.InnerText = "Turbines";
			folderTurbines.AppendChild(folderTurbinesName);
		
			foreach(Turbine turbine in WindFarm.Turbines){
			
				LogAsInfo(String.Format("Adding Turbine {0}",turbine.Name));
				XmlNode turbinePlacemark = template.SelectSingleNode("/kml:kml/kml:Document/kml:Folder/kml:Folder[2]/kml:Placemark", xnm);		
				turbinePlacemark["name"].InnerText = turbine.Name;
				Location turbineGeoLocation = (Location)Toolbox.ReprojectPoint(turbine.Location, Workbook.Geography.Projection, geoProjection);
				double hubHeight = turbine.TurbineType.Height;
				turbinePlacemark["Point"]["coordinates"].InnerText = String.Format("{0},{1},{2}", 
					turbineGeoLocation.X, 
					turbineGeoLocation.Y, 
					hubHeight);		
				if (turbine.IsInstalled){
					turbinePlacemark["styleUrl"].InnerText = "#msn_neighbouring-turbine";
				}else{
					turbinePlacemark["styleUrl"].InnerText = "#msn_proposed-turbine";
				}
			
				turbinePlacemark["Model"]["Location"]["longitude"].InnerText = turbineGeoLocation.X.ToString();
				turbinePlacemark["Model"]["Location"]["latitude"].InnerText = turbineGeoLocation.Y.ToString();
				turbinePlacemark["Model"]["Location"]["altitude"].InnerText = "0.0";
				turbinePlacemark["Model"]["Link"]["href"].InnerText = System.IO.Path.Combine("Model","windmill-1.dae");
				// Scaling
				// windmill-1 hub-height is 5.54m
				double scaleFactor = hubHeight/5.54;
				turbinePlacemark["Model"]["Scale"]["x"].InnerText = scaleFactor.ToString();
				turbinePlacemark["Model"]["Scale"]["y"].InnerText = scaleFactor.ToString();
				turbinePlacemark["Model"]["Scale"]["z"].InnerText = scaleFactor.ToString();
				folderTurbines.AppendChild(doc.ImportNode(turbinePlacemark, true));
			}//turbines
		}//wind Farms

		string kmlFileName = string.Format("{0}.kml", outputFileName);
		string kmlFilePath = System.IO.Path.Combine(currentWorkingDir, kmlFileName);
		doc.Save(kmlFilePath);

		string kmzOutputFileName = System.IO.Path.GetFileNameWithoutExtension(kmlFilePath);
		string kmzOutputFilePath =	System.IO.Path.Combine(currentWorkingDir, string.Format("{0}.kmz", kmzOutputFileName));
		
		if ( PackageAsKmz(kmlFilePath, pathTurbineModel, kmzOutputFilePath) )
		{	
			//Launch output file in google earth (if registered on system)
			System.Diagnostics.Process.Start(kmzOutputFilePath);
		}
			
		// Delete Kml file
		try
		{
			System.IO.File.Delete(kmlFilePath);
		}
		catch (Exception e)
		{
			Toolbox.Log(string.Format("Failed to delete kml file due to {0}.", e.Message), LogLevel.Warn);
		}	
		
		LogAsInfo("Done");
	}
	catch (Exception e)
	{
		Toolbox.Log(e.Message);
		Toolbox.Log(e.StackTrace);
	}
}


public bool PackageAsKmz(string pathToKmlFile, string pathToModelFile, string outputFilePath)
{
	Toolbox.Log("Packaging as KMZ file.");
	string zipExecutable = @"C:\Program Files\7-Zip\7z.exe";
	if (!System.IO.File.Exists(zipExecutable))
	{
		Toolbox.Log("7-zip executable not found in C:\\Program Files. Unable to proceed.", LogLevel.Error);
		return false;
	}
	
	string currentWorkingDir = System.IO.Path.GetDirectoryName(Toolbox.CurrentWorkbookPath);
	if (!System.IO.File.Exists(pathToKmlFile) ||
		!System.IO.File.Exists(pathToModelFile))
	{
		Toolbox.Log("Failed to package as kmz since kml or model files were not found.", LogLevel.Error);
		return false;
	}
	string modelDirectory = System.IO.Path.Combine(currentWorkingDir,"Model");
	if (System.IO.Directory.Exists(modelDirectory))
	{
		Toolbox.Log(string.Format("Directory named Model already exists at {0}", currentWorkingDir), LogLevel.Error);
		return false;
	}
	try
	{
		System.IO.Directory.CreateDirectory(modelDirectory);
	}
	catch(Exception e)
	{
		Toolbox.Log(string.Format("Failed to create necessary directory {0}", e.Message), LogLevel.Error);
		return false;
	}
	
	string targetPath = System.IO.Path.Combine(modelDirectory, "windmill-1.dae");
	try
	{
		System.IO.File.Copy(pathToModelFile, targetPath, true);
		// Remove readonly attribute from copied file
		System.IO.FileAttributes fileAttributes = System.IO.File.GetAttributes(targetPath);
		if ( (fileAttributes & System.IO.FileAttributes.ReadOnly) == System.IO.FileAttributes.ReadOnly )
		{
			System.IO.File.SetAttributes(targetPath, (fileAttributes & ~System.IO.FileAttributes.ReadOnly));
		}
	}
	catch (Exception e)
	{
		Toolbox.Log(string.Format("Failed to copy turbine model locally due to {0}. Turbines will not be displayed in google earth.", e.Message), LogLevel.Warn);
	}
	
	string cmdLineArguments = string.Format("a -tzip {0} {1} {2}",
		System.IO.Path.GetFileName(outputFilePath),
		System.IO.Path.GetFileName(pathToKmlFile),
		"Model");
	
	System.Diagnostics.ProcessStartInfo procStartInfo = new System.Diagnostics.ProcessStartInfo(zipExecutable, cmdLineArguments);
	procStartInfo.UseShellExecute = false;
	procStartInfo.WorkingDirectory = System.IO.Path.GetDirectoryName(pathToKmlFile);	
	System.Diagnostics.Process proc = System.Diagnostics.Process.Start(procStartInfo);
	proc.WaitForExit();
	
	// Clean-up directory create Model Directory
	try
	{
		System.IO.Directory.Delete(modelDirectory, true);
	}
	catch(Exception e)
	{
		Toolbox.Log(string.Format("Failed to delete Model directory: {0}", e.Message), LogLevel.Error);
		return false;
	}
	return true;
}


public void LogAsInfo(string message)
{
	Toolbox.Log(message);
}

public string TriangleBasedOnSectorProbabilities (
	double _sensorLongitude, 
	double _sensorLatitude, 
	double _sensorHeight, 
	double _binCenter, 
	double _binSize, 
	double _sectorProbability)
{ 		
	// WindRose Drawing control [Values optimized for 12 sectors] 
	double fullSectorLength = 5000.0; // distance in meters of 100% probability
	double cutSectorLimitsBy = 5.0;   // reduce sector size for better drawing. Decrease for number of sector > 12

	double meters2latitude = 110540.0;
	double meters2longitude = 111320.0*Math.Cos(_sensorLatitude*Math.PI/180.0);
			
	double fullSectorSizeInDegreesLatitude = fullSectorLength/meters2latitude;
	double fullSectorSizeInDegreesLongitude = fullSectorLength/meters2longitude;

	double binInferiorLimit = 90.0 - (_binCenter - (_binSize*0.5 - cutSectorLimitsBy));
	double binSuperiorLimit = 90.0 - (_binCenter + (_binSize*0.5 - cutSectorLimitsBy));
		
	//point 1 is located on the bin inferior limit
	double pointOneLongitude = _sensorLongitude + Math.Cos(binInferiorLimit*Math.PI/180.0)*
		fullSectorSizeInDegreesLongitude * (_sectorProbability/100.0);
	double pointOneLatitude = _sensorLatitude + Math.Sin(binInferiorLimit*Math.PI/180.0) * 
		fullSectorSizeInDegreesLatitude * (_sectorProbability/100.0);
	//point 2 is located on the bin superior limit
	double pointTwoLongitude = _sensorLongitude + Math.Cos(binSuperiorLimit*Math.PI/180.0) *
		fullSectorSizeInDegreesLongitude * (_sectorProbability/100.0);
	double pointTwoLatitude = _sensorLatitude + Math.Sin(binSuperiorLimit*Math.PI/180.0)* 
		fullSectorSizeInDegreesLatitude * (_sectorProbability/100.0);
			
	return String.Format("{0},{1},{2}\n{3},{4},{5}\n{6},{7},{8}\n",
		_sensorLongitude, 
		_sensorLatitude, 
		_sensorHeight,
		pointOneLongitude, 
		pointOneLatitude, 
		_sensorHeight, 
		pointTwoLongitude, 
		pointTwoLatitude, 
		_sensorHeight); 
}

public Location getCentreOfProject()
{
	var eastingAscending =  from turbine in Workbook.Turbines
							orderby turbine.Location.X ascending
						    select turbine.Location.X;
	double lowestEasting = eastingAscending.FirstOrDefault();
	double highestEasting = eastingAscending.LastOrDefault();
	
	double middleEasting = lowestEasting + ((highestEasting - lowestEasting) / 2);
	
	var northingAscending = from turbine in Workbook.Turbines
							orderby turbine.Location.Y ascending
							select turbine.Location.Y;
		
	double lowestNorthing = northingAscending.FirstOrDefault();
	double highestNorthing = northingAscending.LastOrDefault();
	
	double middleNorthing = lowestNorthing + ((highestNorthing - lowestNorthing) / 2);
	return new Location(middleEasting, middleNorthing);
}