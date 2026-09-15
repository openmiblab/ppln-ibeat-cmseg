import os
import logging

import numpy as np
from tqdm import tqdm
import dbdicom as db
import pyvista as pv
from miblab import pipe


from miblab_plot import mosaic_overlay


PIPELINE = 'T1w_segmentation'

def create_database(
    series,
    case_idx=1,
    visit_idx=2,
    series_idx=3,
    include_substring=None,
    exclude_substring=None,
):
    #### POSSIBLE THAT MULTIPLE SCANS MAY EXIST THEREFORE WE SELECT THE MOST RECENT.
    #### E.G. T1w_1, T1w_2, T1w_3... so we save T1w_3 in the returned database
    latest = {}

    for i in series:
        series_name = i[series_idx][0]

        # include filter (if set, must match)
        if include_substring and include_substring not in series_name:
            continue

        # exclude filter (if set, must NOT match)
        if exclude_substring and exclude_substring in series_name:
            continue

        case_id = i[case_idx]
        visit   = i[visit_idx][0]   # "baseline", "followup"
        #scan    = series_name       # pre/post?  not necessary for T1w to be filtered by this.

        key = (case_id, visit)
        latest[key] = i   # later overwrites earlier *within same visit*

    return list(latest.values())

def run(build, logfile):
    datapath = os.path.join(build, 'T1w_segmentation', 'stage_2_harmonised_T1w')
    maskpath = os.path.join(build, 'T1w_segmentation', 'stage_3_T1w_segmentations')
    displaypath = os.path.join(build, 'T1w_segmentation', 'stage_4_display')


    t1w_db = create_database(db.series(datapath, contains='magnitude'))
    masks_db = db.series(maskpath)

    for series in t1w_db:
        case_id = series[1]
        study_visit = series[2][0]


        png_file = os.path.join(displaypath, f'{case_id}_{study_visit}')
        if os.path.exists(f"{png_file}.png"):
             continue

        mask_case_matched = [m for m in masks_db if m[1] == case_id]
        mask_study_matched = [m for m in mask_case_matched if m[2][0] == study_visit]
        if not mask_study_matched:
            continue

        if len(mask_study_matched) != 1:
            print(f"WARNING! Multiple masks found for case {case_id}_{study_visit}. Proceeding with first")
        mask_series = mask_study_matched[0]

        img_vol = db.volume(series)
        img_arr = img_vol.values

        mask_arr = db.volume(mask_series).values
        
        mask = {
            'LKC': 1,
            'LKM': 2,
            'RKC': 3,
            'RKM': 4
        }

        rois = {}

        for name, value in mask.items():
            rois[name] = (mask_arr == value).astype(int)
        mosaic_overlay(img_arr, rois, png_file, margin=[15,5,2])
        print(f'{png_file} display saved!')



if __name__=='__main__':


    BUILD = r"C:/Users/mdq23at/Documents/ppln-ibeat-cmseg/iBEAt_Build"
    pipe.run_stage(run, BUILD, PIPELINE, __file__)


