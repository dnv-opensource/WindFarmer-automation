import os
import pandas as pd
import geopandas as gpd
import seaborn as sns
import contextily as ctx
from matplotlib import pyplot as plt
import windfarmer.sdk
from System.Collections.Generic import List

               
def get_external_wake_efficiency(wf: windfarmer.sdk.Sdk):
    external_eff = [e for e in wf.Workbook.MonteCarloEnergyModel.Efficiencies.CalculatedEfficiencies if e.Description == "1b Wake effect external"][0]
    return external_eff.CalculatedMean		
                
def get_full_yield_from_results(wf: windfarmer.sdk.Sdk, scenario, subject_farm="target"):
    farm = [f for f in scenario.WindFarms if f.Name == subject_farm][0]
    return scenario.FarmTotalYields.GetVariantResult("Full").GetValueForFarm(farm).Value / 1e6
        
def get_and_remove_other_buildable_areas(wf: windfarmer.sdk.Sdk, area_name):
    list_other_regions = []
    for reg in wf.Workbook.InclusionRegions:
        if reg.Name != area_name:
            list_other_regions.append(reg)
            
    for reg in list_other_regions:
        wf.Workbook.InclusionRegions.Remove(reg.Name)
        
    return list_other_regions
        
def check_neighbour_exists_and_delete_existing_turbines(wf: windfarmer.sdk.Sdk, neighbour_name):
    farm = wf.Workbook.WindFarms[neighbour_name]
    if farm != None:
        if farm.Turbines.Count == 0:
            return
        else:
            wf.Workbook.WindFarms.Remove(neighbour_name)
            
    wf.Toolbox.Log("Creating empty farm named {}".format(neighbour_name))
    empty_farm = wf.Scripting.WindFarm(neighbour_name)
    empty_farm.IsNeighbour = True
    empty_farm.IsIncludedInBlockageCalculation = False
    wf.Workbook.WindFarms.Add(empty_farm)

def plot_lease_area(lease_areas):
    # calculate the centroid for each geometry
    centroids = lease_areas.geometry.centroid

    # convert to background map crs & plot
    lease_areas = lease_areas.to_crs(epsg=3857)
    centroids = centroids.to_crs(epsg=3857)
    ax = lease_areas.plot(figsize=(10, 10), alpha=0.5, edgecolor='k')
    centroids.plot(ax=ax, color='r')

    # adjust plot extents to see the shoreline
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    extension = 0.4  
    new_xlim = (xlim[0] - (xlim[1]-xlim[0])*extension, xlim[1])
    new_ylim = (ylim[0] - (ylim[1]-ylim[0])*extension, ylim[1])
    ax.set_xlim(new_xlim)
    ax.set_ylim(new_ylim)

    # add background
    ctx.add_basemap(ax)
    plt.axis('off')
    plt.show()

def plot_cumulative_dist(path_to_results):
    results = pd.read_csv(path_to_results, sep=',')
    results.drop("Unnamed: 0", axis=1, inplace=True)
    print(results)
    sns.histplot(results['External wake efficiency [%]'], cumulative=True, stat='probability', bins=50, color='grey')
    median = results['External wake efficiency [%]'].quantile(0.5)
    min_val = results['External wake efficiency [%]'].min()
    max_val = results['External wake efficiency [%]'].max()
    plt.xlim(min_val, max_val)
    plt.ylim(0, 1)
    # Add horizontal arrow from x=min_val to x=median at probability=0.5 with dashed style
    plt.arrow(min_val, 0.5, median-min_val, 0, color='red',  length_includes_head=True, head_width=0.05, head_length=0.005)
    # Add vertical arrow from y=0 to y=0.5 at the median with dashed style
    plt.arrow(median, 0.5, 0, -0.5, color='red', length_includes_head=True, width=0.00005, head_width=0.002, head_length=0.09)
    plt.annotate(f'{round(median, 3)}', (median, 0), textcoords="offset points", xytext=(30,10), ha='center', rotation=0, fontsize=12, fontweight='bold', bbox=dict(facecolor='white', edgecolor='none', boxstyle='round,pad=0.2'))
    # Get current yticks
    yticks = plt.yticks()[0]
    # Add a new ytick for the point where the red line crosses the y-axis
    plt.yticks(list(yticks) + [0.5])
    plt.xlabel('External Wake Efficiency of the Extension Project [%]')
    plt.ylabel('Cumulative Probability [-]')
    plt.title('CDF of External Wake Efficiency of the Extension Project\n(50th Percentile Highlighted)')
    # Save the figure with 300 dpi
    plt.savefig('cdf_plot.png', dpi=300)
    plt.show()
    return median
