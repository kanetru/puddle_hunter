# puddle_hunter
Automated Sentinel-2 Water Classification & Inundation Time Series

**Overview**

Puddle Hunter is a reproducible Python-based workflow for automated surface water detection from Sentinel-2 imagery.
It generates spatially consistent water masks and multi-temporal inundation statistics suitable for environmental monitoring, land management analysis, and downstream spatial modelling. 
Puddle Hunter is a Sentinel-2 adaptation of the Fisher, Flood and Danaher WI2015 Landsat image classifier. 

**The Problem**

Standard water classifications such as NDWI have simple two band inputs, however require manual thresholding and commonly misclassify impure pixels. This makes the application of NDWI to inundation time series difficult, as thresholds applied across broad time periods may not be accurate. WI2015 which is used in Puddle Hunter applies a surface reflectance, therefore a simple global threshold can be selected, allowing automated classification of water pixels across images from different places and times. However, the spatial resolution of Landsat imagery is too coarse for the detection of potentially meaningful changes in water inundation. These limit reliability for long-term water monitoring applications.

**The Solution**

Puddle Hunter improves on tradtional NDWI classification by incorporating cloud and shadow mask integration, surface reflectance pre-processing, while improving on the spatial resolution of the Landsat classifier from 30m to 20m. 

**The Workflow**
1. 









