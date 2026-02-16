# puddle_hunter
Automated Sentinel-2 Water Classification & Inundation Time Series

**Overview**

Puddle Hunter is a reproducible Python-based workflow for automated surface water detection from Sentinel-2 imagery.
It generates spatially consistent water masks and multi-temporal inundation statistics suitable for environmental monitoring, land management analysis, and downstream spatial modelling. 
Puddle Hunter is a Sentinel-2 adaptation of the Fisher, Flood and Danaher WI2015 Landsat image classifier. 

**The Problem**

Standard water classifications such as NDWI have simple two band inputs, however require manual thresholding and commonly misclassify impure pixels. This makes the application of NDWI to inundation time series difficult, as thresholds applied across broad time periods may not be accurate. WI2015 which is used in Puddle Hunter applies a surface reflectance, therefore a simple global threshold can be selected, allowing automated classification of water pixels across images from different places and times. However, the spatial resolution of Landsat imagery is too coarse for the detection of potentially meaningful changes in water inundation. These limit reliability for long-term water monitoring applications.

**The Solution**

Puddle Hunter improves on tradtional NDWI classification by incorporating cloud and shadow mask integration, surface reflectance pre-processing, while improving on the spatial resolution of the Landsat classifier from 30m to 10m. 
The following image is a frequency inundation visualisation of the Windorah region during the West Queensland floods between 03-2025 and 06-2025.

![Puddle Hunter Example](windorah_20250301_20250701.jpg)

**The Workflow**

1. Scene Selection via Metadata Query
Sentinel-2 scenes are dynamically retrieved using a PostgreSQL metadata query filtered by tile ID and date range.

2. Automated Data Recall
Required spectral and classification layers (water, cloud, shadow, terrain masks) are programmatically recalled into a working directory.

3. Water Extraction (Base Classification)
Water pixels are extracted from the Sentinel-2 classification layer, producing an initial binary water mask per scene.

4. Cloud, Shadow & Terrain Masking
Cloud and topographic shadow layers are applied to remove contaminated pixels.
Scenes exceeding a cloud coverage threshold (>50%) are automatically excluded.

5. Spatial Alignment & Mask Integration
All mask layers are reprojected and aligned to a common grid to ensure spatial consistency before masking is applied.

6. Temporal Aggregation
Valid masked water rasters are stacked and summed to compute per-pixel water occurrence frequency across the observation period.

7. Occurrence Thresholding
Low-frequency detections are filtered to reduce noise, producing a proportional inundation raster.

8. Optional Tile Mosaic
Multiple tile outputs can be mosaicked into a regional water frequency surface.

**Validation**

The workflow was evaluated using reference aerial imagery, yielding:

Metric	Value
Weighted Kappa	0.65
Weighted Accuracy	0.993
Weighted F1 Score	0.946
Producer Accuracy – Water	0.806
Producer Accuracy – Dry	0.995
User Accuracy – Water	0.989
User Accuracy – Dry	0.902

These results demonstrate high reliability in detecting water pixels while maintaining low false-positive rates for dry areas.







