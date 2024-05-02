import os
import sys
import clr # the pythonnet library required

class Sdk:
    def __init__(self, windfarmer_installation_folder):
        """ Initialise a WindFarmer Analyst instance
        Args:
            windfarmer_installation_folder: path to the windfarmer installation folder
        """
        windfarmer_binary_path = os.path.join(windfarmer_installation_folder, "Bin")
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