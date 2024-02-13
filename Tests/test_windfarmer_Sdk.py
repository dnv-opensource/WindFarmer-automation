# Test import of windfarmer module and connection to sdk
#%% Run script manually
import windfarmer.sdk
windfarmer_installation_folder = r'C:\Program Files\DNV\WindFarmer - Analyst 1.3.6.2'
wf = windfarmer.sdk.Sdk(windfarmer_installation_folder)
print(' > SDK is now up and running!')
