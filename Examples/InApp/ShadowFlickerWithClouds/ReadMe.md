# Shadow flicker assessments, considering cloud cover and wind rose. 

Using the automation module, this script extends the WindFarmer Environment module shadow flicker 
correction capability to make a more "realistic" assessment of the cloud cover alongside the 
theoretical worst case prediction.

A dictionary of fixed rotor orientations with corresponding directional frequencies can be used to
consider the impact of wind direction on the shadow flicker results. Flicker grids and receptor 
results are then simulated for each fixed rotor direction and the frequency weighted sum is calculated 
to define the overall flicker.

A time series of weightings can be applied to the shadow flicker results to scale them to account for 
cloud cover. A weighting of 0.0 means for fully covered skies and will result in zero flicker. 1.0
corresponds to clear sky and the unweighted shadow flicker result would be used. If you apply a 
weighting of 0.5 this halves the flicker prediction from the clear sky case.

The calculation accepts daily weightings but a helper method is provided to convert monthly weightings 
to daily weightings.
