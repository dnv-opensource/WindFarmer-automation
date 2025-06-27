import os
import sys
import pythonnet
import clr_loader

class Sdk:
    def __init__(self, windfarmer_installation_folder, verbose=False):
        """ Initialise a WindFarmer Analyst instance
        Args:
        windfarmer_installation_folder: str
            Path to the windfarmer installation folder.
        verbose: bool, default: False
            If True, will print additional information during initialization.
        """        
        windfarmer_binary_path = os.path.join(windfarmer_installation_folder, "Bin")

        # initialise .net core CLR runtime
        try:
            runtime_config_path = os.path.join(windfarmer_binary_path, "GH.WindFarmer.runtimeconfig.json")
            rt = clr_loader.get_coreclr(runtime_config=str(runtime_config_path))
            pythonnet.set_runtime(rt)
            import clr
            if verbose:
                print(f"Successfullt initialized .NET Core CLR runtime.")
                if hasattr(clr, "__version__"):
                    print(f"clr (pythonnet) version attribute: {clr.__version__}")
                from System import Environment, AppDomain
                from System.Runtime.InteropServices import RuntimeInformation
                print(f"System.Environment.Version: {Environment.Version}")
                print(f"RuntimeInformation.FrameworkDescription: {RuntimeInformation.FrameworkDescription}")
        except Exception as e:
            print(f"ERROR during runtime initialization or clr import: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # Setup WindFarmer SDK
        sys.path.append(windfarmer_binary_path)
        clr.AddReference("System")
        clr.AddReference("System.Collections")
        clr.AddReference('GH.WindFarmer.API')
        clr.AddReference('GH.WindFarmer.Scripting')
        clr.AddReference('GH.PlanningTools.Scripting')        
        
        import Scripting
        sys.path.append(os.path.join(windfarmer_binary_path, 'PythonLibs', 'WindFarmerAPI'))        
        from PyScripting import PyToolbox

        self._Toolbox = PyToolbox()
        self._Scripting = Scripting
        self._Workbook = Scripting.Workbook

    @property
    def Scripting(self):
        """ The windfarmer scripting library, for object construction
        """
        return self._Scripting

    @property
    def Workbook(self):
        """ The workbook
        """
        return self._Workbook

    @property
    def Toolbox(self):
        """ The toolbox
        """
        return self._Toolbox