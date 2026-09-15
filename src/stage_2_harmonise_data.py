"""
Create clean database
"""

import os
import re
import zipfile
import shutil
import logging
import tempfile
import numpy as np
import pydicom

from tqdm import tqdm
import dbdicom as db

import napari



# Helper: Flatten directory after extraction
def flatten_folder(root_folder):
    for dirpath, _, filenames in os.walk(root_folder, topdown=False):
        for filename in filenames:
            src_path = os.path.join(dirpath, filename)
            dst_path = os.path.join(root_folder, filename)

            if os.path.exists(dst_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dst_path):
                    dst_path = os.path.join(root_folder, f"{base}_{counter}{ext}")
                    counter += 1

            shutil.move(src_path, dst_path)

        if dirpath != root_folder:
            try:
                os.rmdir(dirpath)
            except OSError:
                print(f"Could not remove {dirpath} — not empty or in use.")

# Helper: Standardize patient ID
def bari_ibeat_patient_id(folder):
    if folder[:3] == 'iBE':
        return folder[4:].replace('-', '_')
    else:
        return folder[:4] + '_' + folder[4:]

    

def bari_add_series_name(name, all_series:list):

    # If a series is among the first 20, assume it is precontrast
    series_nr = int(name[7:])
    if series_nr < 1000:
        series_name = 'T1w_1_'
    else:
        series_name = 'T1w_1_'
    
    # Increment the number as appropriate
    new_series_name = series_name
    counter = 2
    while new_series_name in all_series:
        new_series_name = series_name.replace('_1_', f'_{counter}_')
        counter += 1
    all_series.append(new_series_name)

# Helper: Standardize patient ID
def bordeaux_ibeat_patient_id(folder):
    # Extract two groups of digits: 4 digits and 3 digits
    match = re.search(r'(\d{4}).*?(\d{3})', folder)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    return None

def bordeaux_ibeat_control_id(basename):
    if basename == 'Bordeaux_Volunteers_Repeatability_Baseline':
        return '2128_C03'
    elif ('001') in basename:
        return '2128_C01'
    elif ('002') in basename:
        return '2128_C02'
    elif ('004_1') in basename:
        return '2128_C04'

def exeter_ibeat_setup_id(basename):
    if ('1') in basename:
        return '3128_S01'
    elif ('2') in basename:
        return '3128_S02'
    elif ('3') in basename:
        return '3128_S03'
    elif ('4') in basename:
        return '3128_S04'  
    elif ('5') in basename:
        return '3128_S05' 

def exeter_ibeat_controls_id(basename):
    if ('V1') in basename:
        return '3128_C01'
    elif ('V2') in basename:
        return '3128_C02'
    elif ('V3') in basename:
        return '3128_C03'
    elif ('V4') in basename:
        return '3128_C04'  
    elif ('V5') in basename:
        return '3128_C05' 

def bari_ibeat_controls_id(basename):
    if ('volunteer1') in basename:
        return '1128_C01'

def exeter_ibeat_patient_id(folder):
    # Extract two groups of digits: 4 digits and 3 digits
    match = re.search(r'(\d{4}).*?(\d{3})', folder)
    if match:
        return f"{match.group(1)}_{match.group(2)}"
    return None


def leeds_ibeat_setup_id(basename):
    match = re.search(r'(\d+)$', basename)

    if not match:
        return None

    setup = int(match.group(1))
    return f'4128_S{setup:02d}'

def turku_ibeat_patient_id(basename):
    digits = ''.join(re.findall(r'\d', basename))
    pid.replace(r'\d')
    pid = f'{digits[:4]}_{digits[-3:]}'
    return pid

def turku_ibeat_control_id(basename):
    digits = ''.join(re.findall(r'\d', basename))
    pid = f'{digits[:4]}_{digits[4:7]}'
    return pid
  

# Helper: Standardize Series Name
def add_series_name(folder, all_series: list):
    new_series_name = "T1w_1_"
    all_series.append(new_series_name)
    return new_series_name

def leeds_ibeat_patient_id(folder):
    # Case 1: iBEAT folders
    if folder.startswith('iBE'):
        return folder[4:].replace('-', '_')
    
    # Case 2: Leeds_Patient_xxxxxxx pattern
    elif 'Leeds_Patient_' in folder:
        folder.split('Leeds_Patient_')[-1]
        pid = folder[-7:]
        return pid[:4] + '_' + pid[4:]
    
    # Case 3: fallback - last 7 digits with split
    else:
        pid = folder[-7:]
        return pid[:4] + '_' + pid[4:]

def leeds_add_series_name(folder, all_series:list):

    # If a series is among the first 20, assume it is precontrast
    name = os.path.basename(folder)
    series_nr = int(name[-2:])
    if series_nr < 2050: 
        series_name = 'T1w_1_'
    else:
        series_name = 'T1w_2_'
    # Add the appropriate number
    new_series_name = series_name
    counter = 2
    while new_series_name in all_series:
        new_series_name = series_name.replace('_1_', f'_{counter}_')
        counter += 1
    all_series.append(new_series_name)    

def exeter_add_series_name(folder, all_series:list):

    series_name = 'T1w_1_'
    # Add the appropriate number
    new_series_name = series_name
    counter = 2
    while new_series_name in all_series:
        new_series_name = series_name.replace('_1_', f'_{counter}_')
        counter += 1
    all_series.append(new_series_name) 

def bordeaux_add_series_name(folder, all_series:list):

    series_name = 'T1w_1_'
    # Add the appropriate number
    new_series_name = series_name
    counter = 2
    while new_series_name in all_series:
        new_series_name = series_name.replace('_1_', f'_{counter}_')
        counter += 1
    all_series.append(new_series_name) 

def sheffield_add_series_name(folder, all_series: list):
    counter = 1

    while f'T1w_{counter}_' in all_series:
        counter += 1

    series_name = f'T1w_{counter}_'
    all_series.append(series_name)  

def turku_add_series_name(folder, all_series: list):
    counter = 1

    while f'T1w_{counter}_' in all_series:
        counter += 1

    series_name = f'T1w_{counter}_'
    all_series.append(series_name) 

def sheffield_ibeat_patient_id(folder):
    id = folder[3:]
    id = id[:4] + '_' + id[4:]
    if id == '2178_157': # Data entry error
        id = '7128_157'
    return id

def leeds_setup(show=False):

    # Leeds site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Leeds", "Leeds_setup_scans")
    sitedatapath = os.path.join(destpath, "Controls", "Leeds") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = leeds_ibeat_setup_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]


        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_series = db.series(temp_folder)
                pat_series = []
                leeds_add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, ('Baseline', 0)]
                vols = []
                for series in multiple_series:
                    series_name = db.unique('ImageType', series)
                    if not 'M' in series_name[0][3]:
                        continue
                    #with tempfile.TemporaryDirectory() as temp_folder:
                        
                    t1w_vol = db.volume(series)
                    if show == True:
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                        napari.run()
                if pat_series[-1] in ('T1w_1_'):
                    series_name = 'magnitude'
                #series_name = input("series? ").strip().lower()
                if series_name == 'magnitude':
                    t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue


def leeds_patients(show=False):

    # Leeds site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Leeds", f"Leeds_Patients")
    sitedatapath = os.path.join(destpath, "Patients", "Leeds") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = leeds_ibeat_patient_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

        if pat_id == "4128_054":

            with tempfile.TemporaryDirectory() as temp_folder:

                series_18 = []
                series_19 = []

                series_zips = sorted(
                    [
                        x for x in all_zip_series
                        if 'series_18-MR' in os.path.basename(x)
                        or 'series_19-MR' in os.path.basename(x)
                    ],
                    key=lambda x: (
                        18 if 'series_18-MR' in os.path.basename(x) else 19,
                        int(
                            os.path.basename(x)
                            .split('-MR')[-1]
                            .replace('.zip', '')
                        )
                    )
                )

                for zip_series in series_zips:

                    base = os.path.basename(zip_series)

                    series_folder = os.path.join(
                        temp_folder,
                        base.replace('.zip', '')
                    )
                    os.makedirs(series_folder, exist_ok=True)

                    try:
                        with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                            zip_ref.extractall(series_folder)

                        series = db.series(series_folder)

                        if 'series_18-MR' in base:
                            series_18.extend(series)

                        elif 'series_19-MR' in base:
                            series_19.extend(series)

                    except Exception as e:
                        logging.error(
                            f"Patient {pat_id} - error processing {zip_series}: {e}"
                        )
                        continue

                magnitude_series = []

                multiple_series = [series_18, series_19]

                for series in multiple_series:

                    img_type = db.unique('ImageType', series[0])

                    if 'M' not in img_type[0][3]:
                        continue
                    else:
                        magnitude_series.append(series)

                    pat_series = []
                    study = [sitedatapath, pat_id, ('Baseline', 0)]
                    leeds_add_series_name(os.path.basename(pat), pat_series)
                    new_series_name = 'magnitude'
                    t1w_clean = study + [(pat_series[-1] + new_series_name, 0)]
                    if t1w_clean in db.series(study):
                        continue
                    try:
                        vols=[]
                        for dicom_folder in magnitude_series:
                            for slice in dicom_folder:
                                vol = db.volume(slice)
                                vol_arr = vol.values
                                vols.append(vol_arr)
                            affine = db.volume(dicom_folder[0]).affine
                        volume = np.stack(vols, axis=-1).squeeze().astype(float)
                        if show == True:
                            viewer = napari.Viewer()
                            viewer.add_image(volume.T, name=f'{pat_series[-1]}')
                            napari.run()
                        db.write_volume((volume, affine), t1w_clean, ref=slice)
                    except Exception as e:
                        print(f'{e}')


        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_series = db.series(temp_folder)
                pat_series = []
                leeds_add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, ('Baseline', 0)]
                vols = []
                for series in multiple_series:
                    series_name = db.unique('ImageType', series)
                    if not 'M' in series_name[0][3]:
                        continue
                    #with tempfile.TemporaryDirectory() as temp_folder:
                        
                    t1w_vol = db.volume(series)
                    if show == True:
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                        napari.run()
                if pat_series[-1] in ('T1w_1_'):
                    series_name = 'magnitude'
                #series_name = input("series? ").strip().lower()
                if series_name == 'magnitude':
                    t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue

def bordeaux_patients(study_type='Baseline', show=False):

    # Bordeaux site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Bordeaux", f"Bordeaux_Patients_{study_type}")
    sitedatapath = os.path.join(destpath, "Patients", "Bordeaux") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = bordeaux_ibeat_patient_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

                        
        
        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_series = db.series(temp_folder)
                pat_series = []
                bordeaux_add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, (study_type, 0)]
                for series in multiple_series:
                    series_name = db.unique('ImageType', series)
                    if not 'M' in series_name[0][3]:
                        continue
                    t1w_vol = db.volume(series)
                    if show == True:
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                        napari.run()
                if pat_series[-1] in ('T1w_1_'):
                    series_name = 'magnitude'
                #series_name = input("series? ").strip().lower()
                if series_name == 'magnitude':
                    t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue

def bordeaux_controls(show=False):

    # Bordeaux site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Bordeaux", "Bordeaux_Volunteers_Repeatability_Baseline")
    sitedatapath = os.path.join(destpath, "Controls", "Bordeaux") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = bordeaux_ibeat_control_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

                        
        
        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_series = db.series(temp_folder)
                pat_series = []
                dataname = os.path.basename(pat)

                bordeaux_add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, (f'Visit1', 0)]
                for series in multiple_series:
                    series_name = db.unique('ImageType', series)
                    if not 'M' in series_name[0][3]:
                        continue
                    t1w_vol = db.volume(series)
                    if show == True:
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                        napari.run()
                if pat_series[-1] in ('T1w_1_'):
                    series_name = 'magnitude'
                #series_name = input("series? ").strip().lower()
                if series_name == 'magnitude':
                    t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue

def exeter_controls(setup_scans=False, show=False):

    # Exeter site paths
    if setup_scans == True:
        sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Exeter", "Exeter_setup_scans")
    else:
        sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Exeter", "Exeter_Volunteer")
    sitedatapath = os.path.join(destpath, "Controls", "Exeter") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        if setup_scans == True:
            pat_id = exeter_ibeat_setup_id(os.path.basename(pat))
        else:
            pat_id = exeter_ibeat_controls_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

                        
        
        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_series = db.series(temp_folder)
                pat_series = []
                exeter_add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, (f'Visit1', 0)]
                for series in multiple_series:
                    series_name = db.unique('ImageType', series)
                    if not 'M' in series_name[0][3]:
                        continue
                    t1w_vol = db.volume(series)
                    if show == True:
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                        napari.run()
                if pat_series[-1] in ('T1w_1_'):
                    series_name = 'magnitude'
                #series_name = input("series? ").strip().lower()
                if series_name == 'magnitude':
                    t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue


def bari_controls(show=False):


    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Bari", "Bari_Volunteers_Repeatability")

    sitedatapath = os.path.join(destpath, "Controls", "Bari") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        pat_id = '1128_C01'

        basename = os.path.basename(pat)
        if ('20201222') in basename:
            visit = 1
        elif ('20210109') in basename:
            visit = 2
        elif ('20210123') in basename:
            visit = 3
        elif ('20210130') in basename:
            visit = 4
            

                

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

                        
        
        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_folders = db.series(temp_folder)
                pat_series = []
                add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, (f'Visit{visit}', 0)]
                series_name = 'magnitude'
                t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                for folder in multiple_folders:
                    split_series = db.split_series(folder, 'ImageType')
                    for imgtype, series in split_series:
                        if not 'M' in imgtype[3]:
                            continue
                        t1w_vol = db.volume(series)
                        if show == True:
                            viewer = napari.Viewer()
                            viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                            napari.run()
                        if pat_series[-1] in ('T1w_1_'):
                            series_name = 'magnitude'
                        #series_name = input("series? ").strip().lower()
                        if series_name == 'magnitude':
                            db.write_volume(t1w_vol, t1w_clean, ref=series)                    
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue
        
def exeter_patients(study_type='Baseline', show=False):

    # Exeter site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Exeter", f"Exeter_Patients_{study_type}")
    sitedatapath = os.path.join(destpath, "Patients", "Exeter") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = exeter_ibeat_patient_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

                        
        
        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_series = db.series(temp_folder)
                pat_series = []
                exeter_add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, (study_type, 0)]
                for series in multiple_series:
                    series_name = db.unique('ImageType', series)
                    if not 'M' in series_name[0][3]:
                        continue
                    t1w_vol = db.volume(series)
                    if show == True:
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                        napari.run()
                if pat_series[-1] in ('T1w_1_'):
                    series_name = 'magnitude'
                #series_name = input("series? ").strip().lower()
                if series_name == 'magnitude':
                    t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue

        
def bari_patients(study_type='Baseline', show=False):

    # Exeter site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Bari", f"Bari_Patients")
    sitedatapath = os.path.join(destpath, "Patients", "Bari") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = bari_ibeat_patient_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue
        
        
        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]

                        
        
        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in sorted(all_zip_series):
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                multiple_folders = db.series(temp_folder)
                pat_series = []
                add_series_name(os.path.basename(pat), pat_series)
                study = [sitedatapath, pat_id, (study_type, 0)]
                series_name = 'magnitude'
                t1w_clean = study + [(pat_series[-1] + f'{series_name}', 0)]
                if t1w_clean in db.series(study):
                    continue
                for folder in multiple_folders:
                    split_series = db.split_series(folder, 'ImageType')
                    for imgtype, series in split_series:
                        if not 'M' in imgtype[3]:
                            continue
                        t1w_vol = db.volume(series)
                        if show == True:
                            viewer = napari.Viewer()
                            viewer.add_image(t1w_vol.values.T, name=f'{pat_series[-1]}')
                            napari.run()
                        if pat_series[-1] in ('T1w_1_'):
                            series_name = 'magnitude'
                        #series_name = input("series? ").strip().lower()
                        if series_name == 'magnitude':
                            db.write_volume(t1w_vol, t1w_clean, ref=series)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue
                
def sheffield_patients():

    # Sheffield site paths
    sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Sheffield")
    sitedatapath = os.path.join(destpath, "Patients", "Sheffield") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        # Get standardized ID
        pat_id = sheffield_ibeat_patient_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue

        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]



        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in all_zip_series:
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                mulitple_folders = db.series(temp_folder)
                pat_series = []
                for folder in mulitple_folders:
                    sheffield_add_series_name(os.path.basename(pat), pat_series)
                    t1w_vol = db.volume(folder)
                    image_types = db.unique('ImageType', folder)
                    split_series = db.split_series(folder, 'ImageType')
                    for type, _ in split_series:
                        if len(split_series) > 1:
                            tqdm.write('more than one types of images in series', type)
                            break
                    if len(mulitple_folders) > 1:
                        print(image_types)
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=pat_series[-1])
                        napari.run()

                    # Construct output study paths
                    study = [sitedatapath, pat_id, ('Baseline', 0)]
                    t1w_clean = study + [(pat_series[-1] + 'magnitude', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=folder)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue

def turku_patients(vendor):

    # Turku site paths
    if vendor == 'GE':
        sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Turku", "Turku_Patients_GE")
    else:
        sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Turku", "Turku_Patients_Philips")

    sitedatapath = os.path.join(destpath, "Patients", "Turku") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):

        if ('5128-001') in os.path.basename(pat):
            pat_id = '5128_001'
        else: 
        # Get standardized ID
            pat_id = turku_ibeat_patient_id(os.path.basename(pat))

        if ('followup') in os.path.basename(pat):
            studytype = 'Followup'
        else:
            studytype = 'Baseline'

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue

        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]



        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in all_zip_series:
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                mulitple_folders = db.series(temp_folder)
                pat_series = []
                for folder in mulitple_folders:
                    add_series_name(os.path.basename(pat), pat_series)
                    try:
                        t1w_vol = db.volume(folder)
                    except:
                        image_types = db.unique('ImageType', folder)
                        tqdm.write('Multiple image types, isolating magnitude...')
                        split_series = db.split_series(folder, 'ImageType')
                        for name, img in split_series:
                            if 'M' not in name:
                                continue
                            else:
                                t1w_vol = db.volume(img)

                    if len(mulitple_folders) > 1:
                        print(image_types)
                        viewer = napari.Viewer()
                        viewer.add_image(t1w_vol.values.T, name=pat_series[-1])
                        napari.run()

                    # Construct output study paths
                    study = [sitedatapath, pat_id, (studytype, 0)]
                    t1w_clean = study + [(pat_series[-1] + 'magnitude', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=folder)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue

def turku_controls(vendor=None, setup=False, show=False):

    # Turku site paths
    if setup == True:
        sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Turku", "Turku_GE_Setup_Tests")
    else:
        if vendor == 'GE':
            sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Turku", "Turku_Volunteers_GE_Repeatability")
        else:
            sitedownloadpath = os.path.join(downloadpath, "BEAt-DKD-WP4-Turku", "Turku_volunteer_repeatability_study")

    sitedatapath = os.path.join(destpath, "Controls", "Turku") 
    os.makedirs(sitedatapath, exist_ok=True)

    # Loop over all patients
    patients = [f.path for f in os.scandir(sitedownloadpath) if f.is_dir()]
    for pat in tqdm(patients, desc='Building clean database'):


        if ('subject_1') in os.path.basename(pat):
            pat_id = '5128_S01'
        else:
            pat_id = turku_ibeat_control_id(os.path.basename(pat))

        # Skip excluded
        # if pat_id in EXCLUDE:
        #     continue

        # Find all zips recursively
        all_zip_series = [
            os.path.join(root, file)
            for root, _, files in os.walk(pat)
            for file in files
            if file.lower().endswith('.zip') and 'OT' not in file
        ]



        # Extract all zips for this patient to one temp folder
        with tempfile.TemporaryDirectory() as temp_folder:
            for zip_series in all_zip_series:
                try:
                    with zipfile.ZipFile(zip_series, 'r') as zip_ref:
                        zip_ref.extractall(temp_folder)
                except Exception as e:
                    logging.error(f"Patient {pat_id} - error extracting {zip_series}: {e}")
                    continue
            flatten_folder(temp_folder)

            # Read combined series
            try:
                scans = db.series(temp_folder)
                pat_series = []
                for scan in scans:
                    turku_add_series_name(os.path.basename(pat), pat_series)
                    image_types = db.unique('ImageType', scan)
                    try:
                        t1w_vol = db.volume(scan)
                    except:
                        tqdm.write('Multiple image types exists, isolating magnitude...')
                        split_series = db.split_series(scan, 'ImageType')
                        for name, img in split_series:
                            if 'M' not in name:
                                continue
                            else:
                                t1w_vol = db.volume(img)

                    if len(scans) > 1:
                        print('img type:', image_types)
                        if show == True:
                            viewer = napari.Viewer()
                            viewer.add_image(t1w_vol.values.T, name=pat_series[-1])
                            napari.run()


                   
                    visit_id = re.search(r'V(\d+)', os.path.basename(pat))
                    if visit_id:
                        visit = int(visit_id.group(1))
                    else:
                        visit = 1

                    # Construct output study paths
                    study = [sitedatapath, pat_id, (f'Visit{visit}', 0)]
                    t1w_clean = study + [(pat_series[-1] + 'magnitude', 0)]
                    if t1w_clean in db.series(study):
                        continue
                    db.write_volume(t1w_vol, t1w_clean, ref=scan)
            except Exception as e:
                logging.error(f"Patient {pat_id} - error reading series: {e}")
                continue


if __name__ == '__main__':
    # Paths
    dir = os.path.join(os.getcwd(), 'iBEAt_Build', 'T1w_segmentation')
    downloadpath = os.path.join(dir, 'stage_1_download')
    destpath = os.path.join(dir, 'stage_2_harmonised_T1w')
    os.makedirs(destpath, exist_ok=True)

    # Logging setup
    logging.basicConfig(
        filename=os.path.join(destpath, 'error.log'),
        filemode='w',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    ##### PATIENTS #####
    for study in ['Baseline', 'Followup']:
        exeter_patients(study_type=study, show=False)
        bordeaux_patients(study_type=study, show=False)
    bari_patients()
    leeds_patients()
    sheffield_patients()
    for vendor in ['GE', 'Philips']:
        turku_patients(vendor)

    #### CONTROLS #####
    bordeaux_controls()
    leeds_setup()
    exeter_controls(setup_scans=True)
    exeter_controls()
    bari_controls()
    for vendor in ['GE', 'Philips']:
        turku_controls(vendor)
    turku_controls(setup=True)
