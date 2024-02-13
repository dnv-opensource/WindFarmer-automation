// Simulate shadow flicker with a cloud cover and wind direction frequency adjusted "realistic" prediction, alongside worst case results
// Overall results, with worst case and "realistic" predictions at receptors are first exported to a TSV file in a folder next to your workbook. This TSV is a text file, open in excel: ShadowFlicker@<date>_<time>_ReceptorResults.tsv
// Then the script continues to compute a releastic flicker grid in .GRD form that may be opened in a GIS tool: AnnualCloudCoverAndWindRoseAveragedShadowFlicker.grd

// Edit the following settings until line 48 with your project specific inputs

// Cloud cover: monthly flicker weightings
// Use 0.0 is fully covered (no flicker for month), 1.0 for clear sky (100% of worst case flicker included for month):
//                                          Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  Oct  Nov  Dec
List<double> monthlyWeightings = new List<double>() {1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0};

// Rotor orientation and wind direction frequency:
// Note, to reduce the grid simulation time you can choose to simulate only half the wind directions. Sum frequency contributions from sectors opposite on the wind rose to do this: 
// A rotor orientation of 0 and 180 degrees leads to the same flicker, if you are happy that ConsiderRotorOffsetFromTower = false is a fair assumption.
Dictionary<int, double> rotorOrientationsAndFrequency = new Dictionary<int, double>()
{// Direcion  Frequency
	{   0,     0.28},
	{  30,     0.21},
	{  60,     0.18},
	{  90,     0.1},
	{ 120,     0.11},
	{ 150,     0.12}
};

public void setRecommendedShadowFlickerSettings()
{
	var flickerSettings = Workbook.ModelSettings.ShadowFlickerSettings;
	flickerSettings.YearOfCalculation = 2024;
	flickerSettings.CalculationTimeInterval = 1; // For faster calculations and testing you can increase this value
	flickerSettings.ConsiderRotorOffsetFromTower = false; 
	flickerSettings.CorrectForTrueNorth = true; 
	flickerSettings.GridHeightAboveGround = 2;
	flickerSettings.MaximumCalculationDistance = 1250; // Check your local requirements
	flickerSettings.MinimumElevationOfSun = 3; // Check your local requirements
	flickerSettings.ModelSunAsDisc = true;
	flickerSettings.UseTerrainVisibilityType = UseTerrainVisibilityType.UseTerrainToCalculateTurbineAndSunVisibility; // for a fast calculation assuming no terrain blocking use: 	UseTerrainVisibilityType.NoCalculationOfVisibilityDueToTerrain
	flickerSettings.LineOfSightResolution = 10.0; 
}

// Resolution for shadow flicker grid calculation
double gridResolution = 25.0;
// Export Options
bool exportToKml = true;
// Receptor flicker image export dimensions:
int imageWidth = 450;
int imageHeight = 700;

public void Execute()
{   
	Toolbox.Log("Starting Shadow Flicker Assessment.");
	
	// Verify that rotor orientation frequencies add up to one
	double sumOfFrequencies = rotorOrientationsAndFrequency.Values.Sum();
	double tolerance = 1E-3;
	if (Math.Abs(sumOfFrequencies - 1.0) > tolerance)
	{
		Toolbox.Log(string.Format("Sum of rotor orientation frequencies dont add up to 1.0, considering a tolerance of {0}. Exiting.", tolerance), LogLevel.Error);
		return;
	}
	
	// Verify that we can run on current workbook. Create outputs directory.
	string artifactsFolderName = string.Format("ShadowFlicker@{0}", DateTime.Now.ToString("ddMMyyy_HHmm"));
	string artifactsDirectoryPath = verifyWorkbookAndCreateArtifactsDirectory(artifactsFolderName);
	if (artifactsDirectoryPath == null)
	{
		Toolbox.Log("An Error has occurred. Exiting.", LogLevel.Error);
		return;	
	}	
	Toolbox.Log(string.Format(" > Results stored in {0}", artifactsDirectoryPath));
		
	// Initialize Settings and Results
	setRecommendedShadowFlickerSettings();
	Dictionary<string, SummaryOfReceptorResults> summaryReceptorResultsList = initializeSummaryOfReceptorResults();
	
	Toolbox.Log(string.Format("Calculating shadow flicker for receptors considering annual cloud cover and wind rose:"));	
	List<double> dailyWeightings = getDailyWeightingsFromMonthlyValues(monthlyWeightings, DateTime.IsLeapYear(Workbook.ModelSettings.ShadowFlickerSettings.YearOfCalculation));
	foreach (int rotorOrientation in rotorOrientationsAndFrequency.Keys)
	{
		setShadowFlickerSettings(rotorOrientationType : RotorOrientationType.UserDefinedRotorOrientation, 
								 rotorOrientation : rotorOrientation);
				
		Scenario shadowFlickerForOrientation = Toolbox.ShadowFlicker.CalculateShadowFlickerAtReceptors(dailyWeightings);
		
		foreach (ReadOnlyReceptorResult receptorResult in shadowFlickerForOrientation.ShadowFlicker.Results.ReceptorResults)
		{
			summaryReceptorResultsList[receptorResult.Name].TotalHoursInYearConsideringCloudCoverAndWindRose += receptorResult.TotalHoursPerYear * rotorOrientationsAndFrequency[rotorOrientation];
		}
		Toolbox.Log(string.Format(" > Direction {0} ... Done.", rotorOrientation));
	}
	
	Toolbox.Log(string.Format("Calculating shadow flicker for receptors for the worst case scenario:"));
	
	setShadowFlickerSettings(rotorOrientationType : RotorOrientationType.SphereAroundRotorCentre); 	
	Scenario worstCase = Toolbox.ShadowFlicker.CalculateShadowFlickerAtReceptors(null);

	foreach (ReadOnlyReceptorResult receptorResult in worstCase.ShadowFlicker.Results.ReceptorResults)
	{
		string chartFilePath = System.IO.Path.Combine(artifactsDirectoryPath, string.Format("{0}.ShadowFlickerChart.png", receptorResult.Name));
		Toolbox.ShadowFlicker.SaveReceptorResultShadowFlickerChartImage(receptorResult, imageWidth, imageHeight, chartFilePath);
		
		// Fill Results for worst case scenario
		summaryReceptorResultsList[receptorResult.Name].DaysOfFlickerPerYear = receptorResult.NumberOfDaysWithFlicker;
		summaryReceptorResultsList[receptorResult.Name].WorstDay = new DateTime(Workbook.ModelSettings.ShadowFlickerSettings.YearOfCalculation, 1, 1).AddDays(receptorResult.WorstDayOfYear -1);
		summaryReceptorResultsList[receptorResult.Name].MinutesOnWorstDay = receptorResult.MinutesOnWorstDay;
		summaryReceptorResultsList[receptorResult.Name].TotalHoursInYearForWorstDay = receptorResult.TotalHoursPerYear;
		foreach (ReadOnlyTurbineFlicker turbineFlicker in receptorResult.TurbineFlickers)
		{
			summaryReceptorResultsList[receptorResult.Name].TurbineNamesContributingToTheEvents.Add(turbineFlicker.Name);
		}
	}
	
	string receptorResultsFilePath = System.IO.Path.Combine( artifactsDirectoryPath, string.Format("{0}_ReceptorResults.tsv", artifactsFolderName));
	exportReceptorResultsToTsv(receptorResultsFilePath, summaryReceptorResultsList.Values);
	Toolbox.Log(string.Format(" > Exported results for {0} receptors.", worstCase.ShadowFlicker.Results.ReceptorResults.Count));
	
	if (exportToKml)
	{		
		string kmlFilePath = System.IO.Path.Combine(artifactsDirectoryPath, string.Format("{0}.kml", artifactsFolderName));
		Toolbox.Log(string.Format("Exporting receptor results to Kml file {0}.", kmlFilePath));
		try
		{
			KmlShadowFlickerReceptors kmlReceptors = new KmlShadowFlickerReceptors(summaryReceptorResultsList.Values);
			KmlShadowFlicker kmlDoc = new KmlShadowFlicker(new KmlShadowFlickerDocument(kmlReceptors));
			KmlShadowFlickerSerializer serializer = new KmlShadowFlickerSerializer();
			serializer.Serialize(kmlFilePath, kmlDoc);
		}
		catch(Exception e)
		{
			Toolbox.Log(string.Format(" > Failed to export KML file due to {0}", e.Message), LogLevel.Error);
			Toolbox.Log(e.Message);
			Toolbox.Log(e.StackTrace);
		}
	}	
	
	Toolbox.Log("Calculating shadow flicker grids considering annual cloud cover, rotor orientation and frequency:");
	Toolbox.ShadowFlicker.GenerateDirectionalShadowFlickerGrids(gridResolution, rotorOrientationsAndFrequency.Keys, rotorOrientationsAndFrequency.Values, artifactsDirectoryPath, "AnnualCloudCoverAndWindRoseAveragedShadowFlicker", dailyWeightings); 
	Toolbox.Log(string.Format(" > Exported grids for {0} directions", rotorOrientationsAndFrequency.Values.Count));
	
	try
	{
		Toolbox.Save();	
	}
	catch(Exception e)
	{
		Toolbox.Log(string.Format("Failed to save workbook. Reason is: {0}", e.Message), LogLevel.Warn);
	}
	
	Toolbox.Log("Ended Shadow Flicker Assessment.");
}

#region Shadow Flicker Calcs

public void setShadowFlickerSettings(RotorOrientationType rotorOrientationType
									, int rotorOrientation = 0) 
{ 	
	Workbook.ModelSettings.ShadowFlickerSettings.RotorOrientationType = rotorOrientationType;
	Workbook.ModelSettings.ShadowFlickerSettings.UserDefinedTurbineOrientation = rotorOrientation;
} 


public void exportReceptorResultsToTsv(string filePath, IEnumerable<SummaryOfReceptorResults> receptorResults)
{
	List<List<string>> header = new List<List<string>>()
	{
		new List<string>{"", "", "", "", "", "", "Total Hours in Year [hrs/yr]", "Total Hours in Year [hrs/yr]", "", "Closest Turbine", "Closest Turbine"},
		new List<string>{"Receptor Name", "UTM Easting [m]", "UTM Northing [m]", "Days per Year", "Worst Day", 	"Minutes On Worst Day", " Worst Case", "Considering annual cloud cover and wind rose", "Turbine Names contributing to the events", "Distance [m]", "Turbine Name"}
	};
	
	using (System.IO.StreamWriter writer = new System.IO.StreamWriter(filePath))
	{
		writer.WriteLine(string.Join("\t", header[0]));
		writer.WriteLine(string.Join("\t", header[1]));
		foreach(SummaryOfReceptorResults result in receptorResults)
		{
			writer.WriteLine(result.ToString());
		}
		Toolbox.Log(string.Format(" > Results file {0} exported.", filePath));
	}	
}

#endregion

#region Utils

public string verifyWorkbookAndCreateArtifactsDirectory(string artifactsFolderName)
{
	if (string.IsNullOrEmpty(Toolbox.CurrentWorkbookPath))
	{
		Toolbox.Log("Error: Workbook needs a location to save calculation outputs. Please save workbook before running.", LogLevel.Error);
		return null;
	}
	string workbookDirectoryPath = System.IO.Path.GetDirectoryName(Toolbox.CurrentWorkbookPath);	
	try
	{
		System.IO.Directory.CreateDirectory(System.IO.Path.Combine(workbookDirectoryPath, artifactsFolderName));
	}
	catch (Exception e)
	{
		Toolbox.Log(string.Format("Error: failed to create outputs directory because {0}. Unable to proceed.", e.Message));
		return null;
	}
	return System.IO.Path.Combine(workbookDirectoryPath, artifactsFolderName);
}

public List<double> getDailyWeightingsFromMonthlyValues(List<double> monthlyWeightings, bool isLeapYear = false)
{
    List<double> dailyWeightings = new List<double>();
    if (monthlyWeightings.Count != 12)
    {
        Toolbox.Log("Error: monthly values does not contain 12 values. Unable to use weightings", LogLevel.Error);
        return dailyWeightings;
    }

    for (int i = 0; i < 12; i++)
    {
        if (i == 0 || i == 2 || i == 4 || i == 6 || i == 7 || i == 9 || i == 11)
        {
            dailyWeightings.AddRange(Enumerable.Repeat<double>(monthlyWeightings[i], 31));
        }
        else if (i == 3 || i == 5 || i == 8 || i == 10)
        {
            dailyWeightings.AddRange(Enumerable.Repeat<double>(monthlyWeightings[i], 30));
        }
        else if (i == 1 & isLeapYear)
        {
            dailyWeightings.AddRange(Enumerable.Repeat<double>(monthlyWeightings[i], 29));
        }
        else // i == 1 & !isLeapYear
        {
            dailyWeightings.AddRange(Enumerable.Repeat<double>(monthlyWeightings[i], 28));
        }
    }
    return dailyWeightings;
}

#endregion

#region Results Data Model

public Dictionary<string, SummaryOfReceptorResults> initializeSummaryOfReceptorResults()
{
	Dictionary<string, SummaryOfReceptorResults> dictionary = new Dictionary<string, SummaryOfReceptorResults>();
	foreach (Receptor receptor in Workbook.Receptors)
	{
		// Calculate closest turbine
		CompareLocations comparer = new CompareLocations(receptor.Location);
		var sortedTurbinesList = Workbook.Turbines.OrderBy(turbine => turbine.Location, comparer);
		var closestTurbine = sortedTurbinesList.FirstOrDefault();
		
		dictionary.Add(receptor.Name, new SummaryOfReceptorResults() 
		{
			ReceptorName = receptor.Name, 
			Easting = receptor.Location.X, 
			Northing = receptor.Location.Y,
			DaysOfFlickerPerYear = 0,
			WorstDay = new DateTime(),
			MinutesOnWorstDay = 0,
			TotalHoursInYearForWorstDay = 0,
			TotalHoursInYearConsideringCloudCoverAndWindRose = 0,
			TurbineNamesContributingToTheEvents = new List<string>(),
			DistanceToClosestTurbineInMeters = comparer.DistanceBetweenLocationsInMeters(receptor.Location, closestTurbine.Location),
			ClosestTurbineName = closestTurbine.Name
		});
	}
	return dictionary;
}

public class SummaryOfReceptorResults
{
	public string ReceptorName { get; set; }
	public double Easting { get; set; }
	public double Northing { get; set; }
	public int DaysOfFlickerPerYear { get; set; }
	public DateTime WorstDay { get; set; }
	public double MinutesOnWorstDay { get; set; }
	public double TotalHoursInYearForWorstDay { get; set; }
	public double TotalHoursInYearConsideringCloudCoverAndWindRose { get; set; }
	public List<string> TurbineNamesContributingToTheEvents { get; set; }
	public double DistanceToClosestTurbineInMeters { get; set; } 
	public string ClosestTurbineName { get; set; }
	
	public override string ToString()
	{	
		return string.Join("\t", new string[]{ this.ReceptorName, this.Easting.ToString("F2"), this.Northing.ToString("F2"), this.DaysOfFlickerPerYear.ToString(), this.WorstDay.ToString("dd-MMM"), this.MinutesOnWorstDay.ToString(), this.TotalHoursInYearForWorstDay.ToString(), this.TotalHoursInYearConsideringCloudCoverAndWindRose.ToString(), string.Join(" ", this.TurbineNamesContributingToTheEvents), this.DistanceToClosestTurbineInMeters.ToString("F2"), this.ClosestTurbineName});
	}
	
	public string ToHtmlTable()
	{
		StringBuilder htmlTable = new StringBuilder();
		htmlTable.Append("<table>");
		htmlTable.Append("<tr><td>");
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Days Per Year", this.DaysOfFlickerPerYear));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Worst Day", this.WorstDay.ToString("dd-MMM")));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Minutes on worst day", this.MinutesOnWorstDay));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Total hours in year for worst case", this.TotalHoursInYearForWorstDay.ToString("F2")));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Total hours in year considering cloud cover and wind rose", this.TotalHoursInYearConsideringCloudCoverAndWindRose.ToString("F2")));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Turbine names contributing to the events", string.Join(" ", this.TurbineNamesContributingToTheEvents)));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Closest turbine distance [m]", this.DistanceToClosestTurbineInMeters.ToString("F2")));
		htmlTable.Append(string.Format("<tr><td>{0}</td><td>{1}</td></tr>", "Closest turbine name", this.ClosestTurbineName));
		htmlTable.Append("</td><td>");
		htmlTable.Append(string.Format("<img src=\"{0}.ShadowFlickerChart.png\" />", this.ReceptorName));
		htmlTable.Append("</td></tr>");
		htmlTable.Append("</table>");
		return htmlTable.ToString();
	}
}

public class CompareLocations : IComparer<I2DLocation>
{
	private I2DLocation referenceLocation;
	
	public CompareLocations(I2DLocation referenceLocation)
	{
		this.referenceLocation = referenceLocation;
	}
		
	public int Compare(I2DLocation location1, I2DLocation location2)
	{
		double distanceBetweenLocation1AndReference = this.DistanceBetweenLocationsInMeters(this.referenceLocation, location1);
		double distanceBetweenLocation2AndReference = this.DistanceBetweenLocationsInMeters(this.referenceLocation, location2);
		if (distanceBetweenLocation1AndReference < distanceBetweenLocation2AndReference)
		{
			// Location 1 is closer to the reference than Location 2
			return -1;
		}
		else if (distanceBetweenLocation1AndReference > distanceBetweenLocation2AndReference)
		{
			// Location 1 is furthest to the reference than Location 2
			return 1;
		}
		else
		{
			return 0;
		}
	}
	
	public double DistanceBetweenLocationsInMeters(I2DLocation location1, I2DLocation location2)
	{
  		return Math.Sqrt(Math.Pow((location2.X - location1.X), 2.0) + Math.Pow((location2.Y - location1.Y) , 2));
	}
}

#endregion

#region Kml Data Model

[System.Xml.Serialization.XmlRootAttribute("kml")]
public class KmlShadowFlicker
{
	private KmlShadowFlickerDocument document;
	
	public KmlShadowFlicker() { }
	
	public KmlShadowFlicker(KmlShadowFlickerDocument document) 
	{
		this.document = document;
	}
	
	[System.Xml.Serialization.XmlElementAttribute("Document")]
	public KmlShadowFlickerDocument Document
	{
		get 
		{
			return this.document;
		}
		set { }
	}
}

public class KmlShadowFlickerDocument
{
	private KmlShadowFlickerReceptors receptors;
	
	public KmlShadowFlickerDocument() {}
		
	public KmlShadowFlickerDocument(KmlShadowFlickerReceptors receptors)
	{
		this.receptors = receptors;
	}
	
	[System.Xml.Serialization.XmlElementAttribute("Folder")]
	public KmlShadowFlickerReceptors Receptors
	{
		get
		{
			return this.receptors;
		}
		set { }
	}
}

public class KmlShadowFlickerReceptors
{	
	public KmlShadowFlickerReceptors() { }
	
	public KmlShadowFlickerReceptors(IEnumerable<SummaryOfReceptorResults> listOfResults)
	{
		receptors = new List<KmlReceptorPlacemark>();
		foreach (SummaryOfReceptorResults result in listOfResults)
		{
			receptors.Add(new KmlReceptorPlacemark(result));
		}
	}
	
	[System.Xml.Serialization.XmlElementAttribute("name")]	
	public string Name
	{
		get
		{
			return "Receptors";
		}
		set { }
	}
	
	[System.Xml.Serialization.XmlElementAttribute("Placemark")]	
	public List<KmlReceptorPlacemark> receptors { get; set; }
}

public class KmlReceptorPlacemark
{
	private SummaryOfReceptorResults receptorResult;
	
	public KmlReceptorPlacemark() { }
	
	public KmlReceptorPlacemark(SummaryOfReceptorResults result)
	{
		this.receptorResult = result;
	}
	
	[System.Xml.Serialization.XmlElementAttribute("name")]
	public string Name
	{
		get 
		{
			return this.receptorResult.ReceptorName;
		}
		set { }
	}
	[System.Xml.Serialization.XmlElementAttribute("Point")]
	public KmlLocation Point 
	{ 
		get
		{
			return new KmlLocation(this.receptorResult.Easting, this.receptorResult.Northing);
		}
		set { }
	}
	[System.Xml.Serialization.XmlElementAttribute("description", typeof(XmlCDataSection))]
	public XmlCDataSection Description
	{
		get
		{
			return new XmlDocument().CreateCDataSection(this.receptorResult.ToHtmlTable());
		}
		set { }
	}
}

public class KmlLocation
{
	private double easting;
	private double northing;
	
	public KmlLocation() { }
	
	public KmlLocation(double easting, double northing)
	{
		this.easting = easting;
		this.northing = northing;
	}

	[System.Xml.Serialization.XmlElementAttribute("coordinates")]
	public string Coordinates
	{
		get 
		{
			Location geoPoint = (Location)Toolbox.ReprojectPoint(new Location(this.easting, this.northing), Workbook.Geography.Projection, Toolbox.GetProjectionFromEpsgCode(4326));
			var coordsString = new StringBuilder();
			coordsString.AppendFormat("{0},", geoPoint.X);
			coordsString.Append(geoPoint.Y);
			return coordsString.ToString();
		}
		set { }
	}
}

public class KmlShadowFlickerSerializer
{
	private const string KML_NAMESPACE = "http://www.opengis.net/kml/2.2";
	
	public void Serialize(string filePath, KmlShadowFlicker document)
	{
		var serializer = new System.Xml.Serialization.XmlSerializer(typeof(KmlShadowFlicker));
		using (var stream = new System.IO.FileStream(filePath, System.IO.FileMode.Create))
		{
			using (var writer = new System.Xml.XmlTextWriter(stream, System.Text.Encoding.Unicode))
			{
				var namespaces = new System.Xml.Serialization.XmlSerializerNamespaces();
				namespaces.Add(string.Empty, KML_NAMESPACE);
				serializer.Serialize(writer, document, namespaces);
			}
		}
	}
}

#endregion

