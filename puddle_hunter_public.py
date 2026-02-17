"""
Puddle Hunter
Public portfolio version.

Certain internal database calls and proprietary utilities have been
abstracted or replaced with placeholders. The core workflow logic,
masking strategy, and temporal aggregation remain unchanged.
"""


import rasterio
from rasterio.io import MemoryFile
import readline
from rasterio.warp import calculate_default_transform, reproject, Resampling
import os, os.path
import glob
from rasterio.merge import merge
import numpy as np
import re
from collections import defaultdict
import pandas as pd
from datetime import datetime,timedelta
import shutil
import psycopg2
import getpass
from rss_da import settings
from rss_da import metadb
from rss_da import qvf, qv
import fnmatch

tile = input("Enter sentinel 2 scene codes, separated by a comma with no space: \n")
start_date = input("Enter start date (YYYYMMDD):\n")
end_date = input("Enter end date (YYYYMMDD): \n")
tiles = tile.split(',')
work_dir = input("Enter work directory path: \n")

def executeSQL(sql):
    """
    execute a single sql statement.
    """

    my_config = settings.config
    my_config.DB_USER = username=getpass.getuser()
    con = metadb.connect(my_config)
    cursor = con.cursor()
    exception = []
    try:
        cursor.execute(sql)
        executed = True
        exception = 'No error'
        try:
            results = cursor.fetchall()
        except:
            results = None
    except psycopg2.Error as e:
        exception.append(e)
        executed = False
        results = None

    con.commit()
    con.close()

    return executed, exception, results

for tile in tiles:
    suffix = tile[2]
    print(f"Processing tile: {tile}")

    sql = f"""
        SELECT *
        FROM imagery_database_of_your_choice
        WHERE tile = '{tile}'
        AND date BETWEEN '{start_date}' AND '{end_date}';
    """
    executed, error, results = executeSQL(sql)

    query_results = pd.DataFrame()

    if executed and results:
        query_results = pd.DataFrame(results)
    else:
        print(f"SQL Execution Failed for tile {tile}. Error: {error}")
        continue

    if query_results.empty:
        print(f"No results found for tile {tile}.")
        continue

    query_results = query_results[query_results.columns[0:5]]
    query_results.iloc[:, 4] = pd.to_datetime(query_results.iloc[:, 4]).dt.strftime('%Y%m%d')

    def format_water_string(row):
        return f"{row[0]}{row[1]}{row[2]}_{row[3]}_{row[4]}_water{suffix}.img"

    water_strings = query_results.apply(format_water_string, axis=1)

    def format_cloud_string(row):
        return f"{row[0]}{row[1]}{row[2]}_{row[3]}_{row[4]}_cloudm{suffix}.img"

    cloud_strings = query_results.apply(format_cloud_string, axis=1)

    def format_cloudshadow_string(row):
        return f"{row[0]}{row[1]}{row[2]}_{row[3]}_{row[4]}_cloudshadowm{suffix}.img"

    cloudshadow_strings = query_results.apply(format_cloudshadow_string, axis = 1)


    def format_toposhadow_string(row):
        return f"{row[0]}{row[1]}{row[2]}_{row[3]}_{row[4]}_toposhadowm{suffix}.img"

    toposhadow_strings = query_results.apply(format_toposhadow_string, axis=1)


    recall_list = water_strings.tolist() + cloud_strings.tolist() + cloudshadow_strings.tolist() + toposhadow_strings.tolist()

    recalldir = r'{}/recall'.format(work_dir)

    if not os.path.exists(recalldir):
        os.makedirs(recalldir)

    qv.recallToHere(recall_list, recalldir)

    tempoutdir = r'{}/temp'.format(recalldir)
    if not os.path.exists(tempoutdir):
        os.makedirs(tempoutdir)



    def water_calculator(input_directory, output_directory):
        for filename in os.listdir(input_directory):
            if "water" in filename:
                input_raster = os.path.join(input_directory, filename)
                output_raster = os.path.join(output_directory, "wiw_unmasked_{}".format(filename))

                with rasterio.open(input_raster) as src:
                    band1 = src.read(1)
                    meta = src.meta.copy()


                reclassified_data = (band1 == 2).astype(np.float32)
                meta.update(dtype=rasterio.float32, count=1)

                with rasterio.open(output_raster, 'w', **meta) as dst:
                    dst.write(reclassified_data, 1)

    water_calculator(recalldir, recalldir)

    def extract_date(filename):
        match = re.search(r'\d{8}', filename)
        return match.group() if match else None

    def masking(input_directory, output_directory):
        mask_files = defaultdict(list)
        input_files = {}
        dates_to_skip = set()

        for filename in os.listdir(input_directory):
            date = extract_date(filename)
            if date:
                full_path = os.path.join(input_directory, filename)
                with rasterio.open(full_path) as src:
                    band1 = src.read(1)

                if "cloud" in filename:
                    mask = (band1 == 1).astype(np.uint8)
                    mask_files[date].append((mask, full_path))

                elif "cloudshadow" in filename or "toposhadow" in filename:
                    if np.sum(band1 == 2) / band1.size > 0.5:
                        dates_to_skip.add(date)
                    else:
                        mask = (band1 == 2).astype(np.uint8)
                        mask_files[date].append((mask, full_path))

                elif "water" in filename:
                    input_files[date] = full_path

        for date in (set(mask_files.keys()) & set(input_files.keys())) - dates_to_skip:
            input_raster = input_files[date]
            output_raster = os.path.join(output_directory, f"masked_{date}.tif")

            with rasterio.open(input_raster) as src:
                input_data = src.read(1).astype(np.float32)
                meta = src.meta.copy()

            combined_mask = np.zeros_like(input_data, dtype=np.uint8)

            for mask_data, mask_raster in mask_files[date]:
                with rasterio.open(mask_raster) as mask_src:
                    transform, width, height = calculate_default_transform(
                        mask_src.crs, src.crs, src.width, src.height, *src.bounds
                    )

                    resampled_mask = np.empty_like(input_data, dtype=np.uint8)
                    reproject(
                        source=mask_data,
                        destination=resampled_mask,
                        src_transform=mask_src.transform,
                        src_crs=mask_src.crs,
                        dst_transform=transform,
                        dst_crs=src.crs,
                        resampling=Resampling.nearest
                    )

                    combined_mask |= resampled_mask

            # Keep water, remove all masked values
            masked_data = np.where(combined_mask == 1, meta.get('nodata', 0), input_data)

            meta.update(dtype=rasterio.float32, count=1, nodata=meta.get('nodata', 0))

            with rasterio.open(output_raster, "w", **meta) as dst:
                dst.write(masked_data, 1)

    masking(recalldir, tempoutdir)

    def count_wiw_occurrences(file_paths):
        occurrence_frequency = None
        total_rasters = len(file_paths)

        for file_path in file_paths:
            with rasterio.open(file_path) as src:
                wiw = src.read(1)

                binary_array = (wiw >= 1).astype(np.uint16)

                if occurrence_frequency is None:
                    occurrence_frequency = binary_array
                else:
                    if binary_array.shape != occurrence_frequency.shape:
                        print(f"Resampling {file_path} from {binary_array.shape} to {occurrence_frequency.shape}")

                        aligned_array = np.zeros(occurrence_frequency.shape, dtype=binary_array.dtype)
                        reproject(
                            source=binary_array,
                            destination=aligned_array,
                            src_transform=src.transform,
                            dst_transform=src.transform,
                            src_crs=src.crs,
                            dst_crs=src.crs,
                            resampling=Resampling.nearest
                        )
                        binary_array = aligned_array
                    occurrence_frequency += binary_array

        return occurrence_frequency

    raster_files = [os.path.join(tempoutdir, file) for file in os.listdir(tempoutdir) if 'masked_' in file and not 'aux' in file]

    obs_number = len(raster_files)

    if not raster_files:
        raise ValueError("No raster files found in {}".format(tempoutdir))

    occurrence_frequency = count_wiw_occurrences(raster_files)
    occurrence_frequency_prop = (occurrence_frequency/obs_number)
    occurrence_frequency_prop[occurrence_frequency_prop < 0.08] = np.nan

    with rasterio.open(raster_files[0]) as src:
        meta = src.meta.copy()

    meta.update(dtype=rasterio.float32, count=1, nodata=0)

    final_output = r'{}/{}_{}{}_complete.tif'.format(work_dir, tile, start_date, end_date)

    with rasterio.open(final_output, 'w', **meta) as dst:
        dst.write(occurrence_frequency_prop, 1)

    print("Congratulations! Your water count raster has been saved to: {}".format(final_output))

    shutil.rmtree(recalldir)

out_fp = r'{}/{}{}_mosaic.tif'.format(work_dir, start_date, end_date)
mosaic_determine = input("Would you like to mosaic your water counts? Y or N: \n").lower()



if mosaic_determine == 'y':
    search_criteria = "*complete.tif" and f"*{start_date}*" and f"*{end_date}*"
    exclude_criteria = "*aux*"

    src_files_to_mosaic = []

    q = os.path.join(work_dir, search_criteria)
    dem_fps = glob.glob(q)

    if len(dem_fps) == 0:
        print(f"No files found in {q}")

    for fp in dem_fps:
        print(f"Found file: {fp}")
        if not fnmatch.fnmatch(fp, exclude_criteria):
            src = rasterio.open(fp)
            src_files_to_mosaic.append(src)

    if len(src_files_to_mosaic) > 0:
      mosaic, out_trans = merge(src_files_to_mosaic)

      out_meta = src.meta.copy()
      out_meta.update({
          "driver": "GTiff",
          "height": mosaic.shape[1],
          "width": mosaic.shape[2],
          "transform": out_trans,
          "crs": src.crs
      })

      with rasterio.open(out_fp, "w", **out_meta) as dest:
          dest.write(mosaic)

    print (f"Thankyou! Your mosaic has been saved to {out_fp}\n")

elif mosaic_determine == 'n':

    print("Thank you!")


