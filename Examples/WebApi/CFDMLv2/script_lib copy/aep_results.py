import pandas as pd

class AEPResultsProcessor:
    """
    A class to process the results of one AEP API call 
    to provide methods to compute the efficiencies and yields over the subject farms.
    and to summarise the results in a dataframe.
    """
    def __init__(self, aep_api_inputs: dict, aep_api_results_all_farms: dict, aep_api_results_subject_farms: dict):
        """
        Initialize the AEPResultsProcessor class.
        :param aep_api_inputs: The input data for the AEP API call.
        :param aep_api_results_all_farms: The results from the AEP API call considering both subject and neighbour wind farms.
        :param aep_api_results_subject_farms: The results from an AEP API call including only the subject farms. Required for CFD.ML calculations to allow delineation of internal and external blockage impacts.
        """
        if aep_api_results_subject_farms is None:
            neighbour_farms = [w for w in aep_api_inputs["windFarms"] if w["isNeighbor"] == True]
            if len(neighbour_farms) > 0 and aep_api_inputs["modelSettings"]["wakeModelType"] == "CFDML":
                raise ValueError("To get a turbine interaction efficiency breakdown, separate AEP results from a calculation only including subject farms are required when running CFD.ML calculations.")
            self.subject_results_dict = aep_api_results_all_farms
        else:
            self.subject_results_dict = aep_api_results_subject_farms
        self.full_results_dict = aep_api_results_all_farms
        self._blockage_model_type = str(aep_api_inputs["energyEfficienciesSettings"]["blockageModel"]["blockageModelType"])
        self._wake_model_type = str(aep_api_inputs["energyEfficienciesSettings"]["wakeModel"]["wakeModelType"])
        self._blockage_correction_efficiency_method = aep_api_inputs["energyEfficienciesSettings"]["blockageModel"][(self._blockage_model_type).lower()]["blockageCorrectionApplicationMethod"]
        self._calculated_efficiencies = aep_api_inputs["energyEfficienciesSettings"]["calculateEfficiencies"]

    # Methods to subject farm total yields and compute efficiencies from the results dictionary
    def get_hysteresis_efficiency(self):
        hysteresisAdjustmentOnAnnualEnergyYield_MWh_per_year = sum([float(x['hysteresisAdjustmentOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict['windFarmAepOutputs']])
        internalWakesOnAnnualEnergyYield_MWh_per_year = sum([float(x['internalWakesOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict['windFarmAepOutputs']])
        return hysteresisAdjustmentOnAnnualEnergyYield_MWh_per_year / internalWakesOnAnnualEnergyYield_MWh_per_year

    # Methods to compute total turbine interaction efficiencies
    def get_total_turbine_interaction_efficiency(self):
        """Get the total turbine interaction efficiency over all subject farms.
        :return: Total turbine interaction efficiency factor.
        """
        int_blockage_efficiency = self.get_internal_blockage_efficiency()
        ext_turbine_interaction_efficiency = self.get_external_turbine_interaction_efficiency()
        internal_wake_efficiency = self.get_internal_wake_efficiency()
        
        total_turbine_interaction_efficiency = int_blockage_efficiency * internal_wake_efficiency * ext_turbine_interaction_efficiency
        return total_turbine_interaction_efficiency

    def get_total_blockage_efficiency(self):
        """Get the total blockage efficiency considering subject and neighbour blockage impacts on subject farms.
        :return: Total blockage efficiency factor.
        """
        return self._get_blockage_efficiency(self.full_results_dict)

    def get_total_wake_efficiency(self):
        """Get the total wake efficiency considering subject and neighbour wake impacts on subject farms.
        :return: Total wake efficiency factor.
        """
        return self.get_external_wake_efficiency() * self.get_internal_wake_efficiency()

    def _get_blockage_efficiency(self, results_dict):
        """Get the blockage efficiency over all farms in the specified results dict.
        :return: Blockage efficiency factor."""
        blockage_correction_efficiency = -1
        if self._blockage_correction_efficiency_method == "OnEnergy":
            blockage_correction_efficiency = float(results_dict["weightedBlockageEfficiency"])
        elif self._blockage_correction_efficiency_method == "OnWindSpeed":
            if self._calculated_efficiencies == False:
                print("Efficiencies were not calculated in the API call, but the OnWindSpeed option was selected. We can't quantify blockege correction efficiency")
                return 1.0
            blockage_on_aep_MWh_per_year = sum([float(x['blockageOnAnnualEnergyYield_MWh_per_year']) for x in results_dict["windFarmAepOutputs"]])
            gross_aep_MWh_per_year = sum([float(x['grossAnnualEnergyYield_MWh_per_year']) for x in results_dict["windFarmAepOutputs"]])
            blockage_correction_efficiency = blockage_on_aep_MWh_per_year / gross_aep_MWh_per_year
        else:
            print("blockage_correction_application_method not recognised")
        return blockage_correction_efficiency   
    
    # internal turbine interaction efficiency methods
    def get_internal_blockage_efficiency(self):
        """Get the internal blockage efficiency over all subject farms.
        Internal Blockage = InternalBlockageOn / Gross

        :return: Internal blockage efficiency.
        """
        return self._get_blockage_efficiency(self.subject_results_dict)

    def get_internal_turbine_interaction_efficiency(self):
        """Get the internal wake turbine interaction efficiency considering only subject farms.

        :return: Internal wake efficiency.
        """
        return self.get_internal_wake_efficiency() * self.get_internal_blockage_efficiency()
    
    def get_internal_wake_efficiency(self):
        """Get the internal wake efficiency over all subject farms.
        Internal Wake = InternalWakeOn / InternalBlockageOn

        :return: Internal wake efficiency factor.
        """
        intWakesOnAnnualEnergyYield_MWh_per_year = sum([float(x['internalWakesOnAnnualEnergyYield_MWh_per_year']) for x in self.subject_results_dict["windFarmAepOutputs"]])
        intBlockageOnAnnualEnergyYield_MWh_per_year = sum([float(x['blockageOnAnnualEnergyYield_MWh_per_year']) for x in self.subject_results_dict["windFarmAepOutputs"]])
        
        if self._wake_model_type != "CFDML":
            # internal LWF impacts non-zero. 
            # Due to ordering, of calculation we need to factor out a possible hysteresis adjustment efficiency
            intLwfCorrectionOnAnnualEnergyYield_MWh_per_year = sum([float(x['largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year']) for x in self.subject_results_dict["windFarmAepOutputs"]])
            intHysteresisAdjustmentOnAnnualEnergyYield_MWh_per_year = sum([float(x['hysteresisAdjustmentOnAnnualEnergyYield_MWh_per_year']) for x in self.subject_results_dict["windFarmAepOutputs"]])
            internal_lwf_correction_efficiency = intLwfCorrectionOnAnnualEnergyYield_MWh_per_year / intHysteresisAdjustmentOnAnnualEnergyYield_MWh_per_year
        else:
            internal_lwf_correction_efficiency = 1.0

        return intWakesOnAnnualEnergyYield_MWh_per_year / intBlockageOnAnnualEnergyYield_MWh_per_year * internal_lwf_correction_efficiency
    
    # external turbine interaction efficiency methods
    def get_external_turbine_interaction_efficiency(self):
        """Get the external wake turbine interaction efficiency, that is the extra turbine interaction effect on subject farms due to adding neighbouring farms.
        :return: External turbine interaction efficiency.
        """
        # this yield is calculated using a subject farm only CFD.ML blockage correction, the same result if we use full or subject results
        largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year = sum([float(x['largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict["windFarmAepOutputs"]])
        # this yield is calculated using a subject and neighbour farms in the CFD.ML blockage corrections
        neighborsWakesOnAnnualEnergyYield_MWh_per_year = sum([float(x['neighborsWakesOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict["windFarmAepOutputs"]])
        # the following then includes the impact of both wakes and blockage from the neighbours
        return neighborsWakesOnAnnualEnergyYield_MWh_per_year / largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year
    
    def _get_lwf_aep_with_external_blockage_energy_loss(self):
        # this yield is calculated using a subject farm only CFD.ML blockage correction, the same result if we use full or subject results
        largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year = sum([float(x['largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict["windFarmAepOutputs"]])
        return largeWindFarmCorrectionOnAnnualEnergyYield_MWh_per_year * self.get_external_blockage_efficiency()
    
    def get_external_blockage_efficiency(self):
        """Get the external blockage efficiency, the extra blockage impact on subject farms due to adding neighbouring wind farms
        :return: External blockage efficiency.
        """
        blockageOnAnnualEnergyYield_MWh_per_year_all_farms = sum([float(x['blockageOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict["windFarmAepOutputs"]])
        blockageOnAnnualEnergyYield_MWh_per_year_subject_farms = sum([float(x['blockageOnAnnualEnergyYield_MWh_per_year']) for x in self.subject_results_dict["windFarmAepOutputs"]])
        return blockageOnAnnualEnergyYield_MWh_per_year_all_farms / blockageOnAnnualEnergyYield_MWh_per_year_subject_farms
    
    def get_external_wake_efficiency(self):
        """Get the external wake efficiency, the extra wake impact on subject farms due to adding neighbouring wind farms
        :return: External wake efficiency.
        """

        neighborsWakesOnAnnualEnergyYield_MWh_per_year = sum([float(x['neighborsWakesOnAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict["windFarmAepOutputs"]])

        return neighborsWakesOnAnnualEnergyYield_MWh_per_year / self._get_lwf_aep_with_external_blockage_energy_loss()

    # Yield getting methods
    def get_full_yield(self):
        """Get the total full yield over all subject farms.
        :return: Full yield in GWh/year.
        """
        full_yield = sum([float(x['fullAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict["windFarmAepOutputs"]]) / 1e3

        if self._blockage_correction_efficiency_method == "OnEnergy":
            blockage_correction_efficiency = float(self.full_results_dict["weightedBlockageEfficiency"])
            full_yield = full_yield * blockage_correction_efficiency

        return full_yield

    def get_gross_yield(self):
        """Get the total gross yield over all subject farms.
        :return: Gross yield in GWh/year.
        """
        gross = sum([float(x['grossAnnualEnergyYield_MWh_per_year']) for x in self.full_results_dict['windFarmAepOutputs']]) / 1e3
        return gross

    # Reporting methods
    def get_results_summary_df(self):
        """Summarise the aep results and available efficiencies in a dataframe.
        :return: Dataframe with the results.
        """
        wind_farm_names = str.join(", ", [x['windFarmName'] for x in self.full_results_dict['windFarmAepOutputs']])

        # summing yields over all subject farms:
        full_yield = self.get_full_yield()
        gross_yield = self.get_gross_yield()
        total_losses = full_yield / gross_yield
        
        # Calculation settings:
        calculation_settings = (
            f"Wakes: {self._wake_model_type}, "
            f"Blockage: {self._blockage_model_type}, "
            f"Blockage application method: {self._blockage_correction_efficiency_method}"
        )

        # make a dataframe for reporting
        case_summary = pd.DataFrame()
        case_summary.index = [wind_farm_names]
        case_summary["Calculation settings"] = [calculation_settings]
        case_summary["Gross Yield [GWh/Annum]"] = [gross_yield]
        if self._calculated_efficiencies == True:
            case_summary["Total turbine interaction efficiency [%]"] = [ self.get_total_turbine_interaction_efficiency() * 100]
            case_summary["Total turbine interaction efficiency - internal farms only [%]"] = [self.get_internal_turbine_interaction_efficiency() * 100]
            case_summary["Internal blockage efficiency [%]"] = [self.get_internal_blockage_efficiency() * 100]
            case_summary["Internal wake efficiency [%]"] = [self.get_internal_wake_efficiency() * 100]
            case_summary["Total turbine interaction efficiency - impact of external farms [%]"] = [self.get_external_turbine_interaction_efficiency() * 100]
            case_summary["External blockage efficiency [%]"] = [self.get_external_blockage_efficiency() * 100]
            case_summary["External wake efficiency [%]"] = [self.get_external_wake_efficiency() * 100]

            case_summary["Alternative breakdown:"] = ["Total wakes and blockage components, with impacts from all farms considered."]
            case_summary["Total Blockage efficiency [%]"] = [self.get_total_blockage_efficiency() * 100]
            case_summary["Total wake efficiency [%]"] = [self.get_total_wake_efficiency() * 100]
            
            case_summary["Total modelled losses [%]"] = [total_losses *100]
        else: 
            case_summary["Blockage efficiency [%]"] = [self.get_total_blockage_efficiency() * 100]
            case_summary["Total modelled losses [%]"] = [total_losses *100]
        case_summary["Full Yield [GWh/Annum]"] = [full_yield]

        case_summary.T.round(1)
        return case_summary