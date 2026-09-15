
import os
import shutil

import dbdicom as db
import numpy as np
import napari
import vreg

from magicgui import magicgui
from qtpy.QtCore import QObject, QEvent
from qtpy.QtWidgets import QMessageBox
from tqdm import tqdm

def create_database(
    series,
    case_idx=1,
    visit_idx=2,
    series_idx=3,
    include_substring=None,
    exclude_substring=None,
):
    """""
    POSSIBLE THAT MULTIPLE SCANS MAY EXIST THEREFORE WE SELECT THE LATEST.
    E.G. T1w_1, T1w_2, T1w_3... so we save T1w_3 in the returned database
    """
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

        key = (case_id, visit) # kept constant
        latest[key] = i   # later overwrites earlier *within same visit*

    return list(latest.values())

def delete_existing_mask(destdir, pid, study_type, mask_name):
    """
    Find and delete an existing kidney mask series directory
    from the correct Baseline/Followup study.

    Example:

    Patient__2128_002
        └── Study__1__Followup
            └── Series__1__T1w_1_LKC

    mask_name:
        T1w_1_LKC
    """

    # --------------------------------------------------------------
    # Patient directory
    # --------------------------------------------------------------

    patient_dir = os.path.join(
        destdir,
        'Patient__' + pid
    )

    if not os.path.isdir(patient_dir):

        print(
            f'Patient directory not found:\n'
            f'{patient_dir}'
        )

        return False

    # --------------------------------------------------------------
    # Find correct Baseline/Followup study
    # --------------------------------------------------------------

    study_dir = None

    for dirname in os.listdir(patient_dir):

        if not dirname.startswith('Study__'):
            continue

        if dirname.endswith(f'__{study_type}'):

            candidate = os.path.join(
                patient_dir,
                dirname
            )

            if os.path.isdir(candidate):

                study_dir = candidate
                break

    if study_dir is None:

        print(
            f'Could not find {study_type} study for {pid}.'
        )

        return False

    # --------------------------------------------------------------
    # Find Series__...__mask_name
    # --------------------------------------------------------------

    mask_dir = None

    for dirname in os.listdir(study_dir):

        if dirname.endswith(f'__{mask_name}'):

            candidate = os.path.join(
                study_dir,
                dirname
            )

            if os.path.isdir(candidate):

                mask_dir = candidate
                break

    if mask_dir is None:

        print(
            f'Could not find existing {mask_name} directory in:'
        )

        print(study_dir)

        return False

    # --------------------------------------------------------------
    # Delete mask directory
    # --------------------------------------------------------------

    print(
        f'Deleting existing mask directory:\n'
        f'{mask_dir}'
    )

    shutil.rmtree(mask_dir)

    # --------------------------------------------------------------
    # Delete index.json
    # --------------------------------------------------------------

    index_log = os.path.join(
        destdir,
        'index.json'
    )

    if os.path.exists(index_log):

        print(
            f'Deleting log:\n'
            f'{index_log}'
        )

        os.remove(index_log)

    else:

        print(
            f'No index.json found at:\n'
            f'{index_log}'
        )

    return True


class CloseWarningFilter(QObject):
    """
    Intercepts the Napari window close button and asks
    the user to confirm before closing.
    """

    def __init__(
        self,
        viewer,
        pid,
        saved_lkc,
        saved_lkm,
        saved_rkc,
        saved_rkm,
        finished
    ):

        super().__init__()

        self.viewer = viewer
        self.pid = pid

        self.saved_lkc = saved_lkc
        self.saved_lkm = saved_lkm
        self.saved_rkc = saved_rkc
        self.saved_rkm = saved_rkm

        self.finished = finished

    def eventFilter(self, obj, event):

        if event.type() == QEvent.Close:

            # ------------------------------------------------------
            # Build status message
            # ------------------------------------------------------

            saved = []

            if self.saved_lkc['value']:
                saved.append('LKC')

            if self.saved_lkm['value']:
                saved.append('LKM')

            if self.saved_rkc['value']:
                saved.append('RKC')

            if self.saved_rkm['value']:
                saved.append('RKM')

            if len(saved) == 4:

                status = (
                    'LKC, LKM, RKC and RKM have been saved.'
                )

            elif len(saved) > 0:

                status = (
                    'Saved: '
                    + ', '.join(saved)
                    + '\n'
                    + 'Not saved: '
                    + ', '.join(
                        structure
                        for structure in [
                            'LKC',
                            'LKM',
                            'RKC',
                            'RKM'
                        ]
                        if structure not in saved
                    )
                    + '.'
                )

            else:

                status = (
                    'No new cortex/medulla masks have been saved.'
                )

            # ------------------------------------------------------
            # Ask user whether to close
            # ------------------------------------------------------

            answer = QMessageBox.question(
                obj,
                'Close viewer',
                (
                    f'{self.pid}\n\n'
                    f'{status}\n\n'
                    'Are you sure you want to close the viewer?'
                ),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            # ------------------------------------------------------
            # User chose Yes
            # ------------------------------------------------------

            if answer == QMessageBox.Yes:

                self.finished['value'] = True

                return False

            # ------------------------------------------------------
            # User chose No
            # ------------------------------------------------------

            event.ignore()

            return True

        return False


def draw_cortex_medulla(group, site, start_from=None, case_id=None):

    dir = os.path.join(
        os.getcwd(),
        'iBEAt_Build',
        'T1w_segmentation'
    )

    database = os.path.join(
        dir,
        'stage_2_harmonised_T1w',
        group,
        site
    )

    destdir = os.path.join(
        dir,
        'stage_3_T1w_segmentations',
        group,
        site
    )

    os.makedirs(
        destdir,
        exist_ok=True
    )

    # ==============================================================
    # Find T1w scans
    # ==============================================================

    t1w_scans = create_database(db.series(
        database,
        contains='magnitude'
    ))


    # --------------------------------------------------------------
    # Get available case IDs
    # --------------------------------------------------------------

    available_cases = {
        f'{series[1]}_{series[2][0]}'
        for series in t1w_scans
    }

    # --------------------------------------------------------------
    # Check start_from
    # --------------------------------------------------------------

    if start_from and start_from not in available_cases:

        print(
            f'\nERROR: "{case_id}" '
            'Check id.' \
            ' Format should be pid_study,' \
            ' e.g. 2128_001_Followup'
        )


        return

    # --------------------------------------------------------------
    # Check case_id
    # --------------------------------------------------------------

    if case_id and case_id not in available_cases:

        print(
            f'\nERROR: Check id.' \
            ' Format should be pid_study,' \
            ' e.g. 2128_001_Followup'
        )

        return

    for series in tqdm(t1w_scans, desc='Segmentation Task', unit='case'):

        pat_series = 'T1w_1_'

        pid = series[1]
        study_type = series[2][0]

        # ----------------------------------------------------------
        # Case filtering
        # ----------------------------------------------------------

        if start_from:

            if f'{pid}_{study_type}' != start_from:

                continue

            print(
                f'\nStarting from case {start_from}'
            )

            # Disable start filter once case is reached
            start_from = None


        if case_id:

            if f'{pid}_{study_type}' != case_id:

                continue

            print(
                f'\nProcessing only case {case_id}'
            )
            


        # ----------------------------------------------------------
        # dbdicom study identifier
        # ----------------------------------------------------------

        study = [
            destdir,
            pid,
            (study_type, 0)
        ]

        # ----------------------------------------------------------
        # Expected LKC/LKM/RKC/RKM series
        # ----------------------------------------------------------

        lkc_mask_clean = study + [
            (pat_series + 'LKC', 0)
        ]

        lkm_mask_clean = study + [
            (pat_series + 'LKM', 0)
        ]

        rkc_mask_clean = study + [
            (pat_series + 'RKC', 0)
        ]

        rkm_mask_clean = study + [
            (pat_series + 'RKM', 0)
        ]

        # ==========================================================
        # Check whether masks already exist
        # ==========================================================

        existing_series = db.series(
            study
        )

        lkc_exists = lkc_mask_clean in existing_series
        lkm_exists = lkm_mask_clean in existing_series
        rkc_exists = rkc_mask_clean in existing_series
        rkm_exists = rkm_mask_clean in existing_series

        if lkc_exists:
            print(
                f'{pid}_{study_type}: LKC already exists.'
            )

        if lkm_exists:
            print(
                f'{pid}_{study_type}: LKM already exists.'
            )


        if rkc_exists:
            print(
                f'{pid}_{study_type}: RKC already exists.'
            )


        if rkm_exists:
            print(
                f'{pid}_{study_type}: RKM already exists.'
            )


        # ----------------------------------------------------------
        # If all four already exist, skip patient
        # ----------------------------------------------------------

        if (
            lkc_exists
            and lkm_exists
            and rkc_exists
            and rkm_exists
        ):

            print(
                f'{pid}_{study_type}: '
                'LKC, LKM, RKC and RKM already exist — skipping.'
            )

            continue

        # ==========================================================
        # Load T1w
        # ==========================================================

        t1w_vol = db.volume(
            series
        )

        print(
            f'\nOpening {pid}_{study_type}'
        )

        t1w_arr = t1w_vol.values.T

        # ==========================================================
        # Open Napari
        # ==========================================================

        viewer = napari.Viewer()

        viewer.add_image(
            t1w_arr,
            name='T1w'
        )

        # ----------------------------------------------------------
        # Track whether each structure has been saved
        # ----------------------------------------------------------

        saved_lkc = {
            'value': False
        }

        saved_lkm = {
            'value': False
        }

        saved_rkc = {
            'value': False
        }

        saved_rkm = {
            'value': False
        }

        finished = {
            'value': False
        }

        # ==========================================================
        # Kidney assignment widget
        # ==========================================================

        @magicgui(
            object_1={
                'label': 'T1w - object 1',
                'choices': [
                    'Select...',
                    'LKC',
                    'LKM',
                    'RKC',
                    'RKM'
                ]
            },
            object_2={
                'label': 'T1w - object 2',
                'choices': [
                    'Select...',
                    'LKC',
                    'LKM',
                    'RKC',
                    'RKM'
                ]
            },
            object_3={
                'label': 'T1w - object 3',
                'choices': [
                    'Select...',
                    'LKC',
                    'LKM',
                    'RKC',
                    'RKM'
                ]
            },
            object_4={
                'label': 'T1w - object 4',
                'choices': [
                    'Select...',
                    'LKC',
                    'LKM',
                    'RKC',
                    'RKM'
                ]
            },
            call_button='Save'
        )
        def cortex_medulla_assignment(
            object_1='Select...',
            object_2='Select...',
            object_3='Select...',
            object_4='Select...'
        ):

            print(
                '\n--------------------------------'
            )

            print(
                f'Processing {pid}_{study_type}'
            )

            print(
                '--------------------------------'
            )

            print(
                f'Object 1 → {object_1}'
            )

            print(
                f'Object 2 → {object_2}'
            )

            print(
                f'Object 3 → {object_3}'
            )

            print(
                f'Object 4 → {object_4}'
            )

            # ======================================================
            # Store assignments
            # ======================================================

            assignments = {
                'object 1 - T1w': object_1,
                'object 2 - T1w': object_2,
                'object 3 - T1w': object_3,
                'object 4 - T1w': object_4
            }

            # ======================================================
            # At least one object must be assigned
            # ======================================================

            assigned = [
                value
                for value in assignments.values()
                if value != 'Select...'
            ]

            if len(assigned) == 0:

                print(
                    f'{pid}_{study_type}: '
                    'No object has been assigned.'
                )

                QMessageBox.warning(
                    viewer.window._qt_window,
                    'No structure assigned',
                    (
                        'Please assign at least one object '
                        'to LKC, LKM, RKC or RKM.'
                    )
                )

                return

            # ======================================================
            # Prevent two objects being assigned to same structure
            # ======================================================

            if len(assigned) != len(set(assigned)):

                duplicates = []

                for structure in [
                    'LKC',
                    'LKM',
                    'RKC',
                    'RKM'
                ]:

                    if assigned.count(structure) > 1:

                        duplicates.append(
                            structure
                        )

                print(
                    f'{pid}_{study_type}: Duplicate assignment: '
                    f'{duplicates}'
                )

                QMessageBox.warning(
                    viewer.window._qt_window,
                    'Invalid assignment',
                    (
                        'The following structure(s) have been '
                        'assigned to more than one object:\n\n'
                        + ', '.join(duplicates)
                        + '\n\n'
                        'Each structure can only be assigned '
                        'to one object.'
                    )
                )

                return

            # ======================================================
            # nnInteractive layer names
            # ======================================================

            object_names = [
                'object 1 - T1w',
                'object 2 - T1w',
                'object 3 - T1w',
                'object 4 - T1w'
            ]

            # ======================================================
            # Check assigned objects actually exist
            # ======================================================

            for object_name, assignment in assignments.items():

                if assignment == 'Select...':
                    continue

                if object_name not in viewer.layers:

                    print(
                        f'{pid}_{study_type}: '
                        f'{object_name} not found.'
                    )

                    QMessageBox.warning(
                        viewer.window._qt_window,
                        'Object not found',
                        (
                            f'{object_name} was assigned to '
                            f'{assignment}, but the layer does not exist.'
                        )
                    )

                    return

            # ======================================================
            # Extract assigned objects
            # ======================================================

            structure_arrays = {
                'LKC': None,
                'LKM': None,
                'RKC': None,
                'RKM': None
            }

            for object_name, assignment in assignments.items():

                if assignment == 'Select...':
                    continue

                object_arr = (
                    viewer.layers[object_name]
                    .data
                    .T
                    .astype(int)
                )

                structure_arrays[assignment] = object_arr

            # ======================================================
            # Class mapping
            #
            # LKC = 1
            # LKM = 2
            # RKC = 3
            # RKM = 4
            # ======================================================

            class_values = {
                'LKC': 1,
                'LKM': 2,
                'RKC': 3,
                'RKM': 4
            }

            # ======================================================
            # Re-check current database state
            # ======================================================

            existing_series = db.series(
                study
            )

            lkc_exists_now = (
                lkc_mask_clean in existing_series
            )

            lkm_exists_now = (
                lkm_mask_clean in existing_series
            )

            rkc_exists_now = (
                rkc_mask_clean in existing_series
            )

            rkm_exists_now = (
                rkm_mask_clean in existing_series
            )

            save_structure = {
                'LKC': structure_arrays['LKC'] is not None,
                'LKM': structure_arrays['LKM'] is not None,
                'RKC': structure_arrays['RKC'] is not None,
                'RKM': structure_arrays['RKM'] is not None
            }

            exists_now = {
                'LKC': lkc_exists_now,
                'LKM': lkm_exists_now,
                'RKC': rkc_exists_now,
                'RKM': rkm_exists_now
            }

            mask_clean = {
                'LKC': lkc_mask_clean,
                'LKM': lkm_mask_clean,
                'RKC': rkc_mask_clean,
                'RKM': rkm_mask_clean
            }

            # ======================================================
            # Check existing structures and ask about overwrite
            # ======================================================

            for structure in [
                'LKC',
                'LKM',
                'RKC',
                'RKM'
            ]:

                if (
                    save_structure[structure]
                    and exists_now[structure]
                ):

                    answer = QMessageBox.question(
                        viewer.window._qt_window,
                        f'{structure} mask already exists',
                        (
                            f'{pid}_{study_type}: '
                            f'{structure} mask already exists.\n\n'
                            'Do you want to overwrite it?'
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )

                    if answer == QMessageBox.Yes:

                        print(
                            f'{pid}_{study_type}: '
                            f'{structure} overwritten.'
                        )

                        deleted = delete_existing_mask(
                            destdir,
                            pid,
                            study_type,
                            pat_series + structure
                        )

                        if not deleted:

                            print(
                                f'{pid}_{study_type}: '
                                f'{structure} deletion failed.'
                            )

                            QMessageBox.warning(
                                viewer.window._qt_window,
                                f'{structure} deletion failed',
                                (
                                    f'The existing {structure} mask '
                                    'could not be deleted.\n\n'
                                    f'{structure} will not be overwritten.'
                                )
                            )

                            save_structure[structure] = False

                    else:

                        print(
                            f'{pid}_{study_type}: '
                            f'{structure} exists — not overwritten.'
                        )

                        save_structure[structure] = False

            # ======================================================
            # Save structures
            # ======================================================

            for structure in [
                'LKC',
                'LKM',
                'RKC',
                'RKM'
            ]:

                if not save_structure[structure]:
                    continue

                structure_arr = structure_arrays[structure]

                # --------------------------------------------------
                # Force foreground to correct class
                # --------------------------------------------------

                structure_arr[structure_arr > 0] = (
                    class_values[structure]
                )

                structure_vol = vreg.volume(
                    structure_arr,
                    t1w_vol.affine
                )

                db.write_volume(
                    structure_vol,
                    mask_clean[structure],
                    ref=series
                )

                # --------------------------------------------------
                # Update saved status
                # --------------------------------------------------

                if structure == 'LKC':

                    saved_lkc['value'] = True

                elif structure == 'LKM':

                    saved_lkm['value'] = True

                elif structure == 'RKC':

                    saved_rkc['value'] = True

                elif structure == 'RKM':

                    saved_rkm['value'] = True

                print(
                    f'{pid}_{study_type}: '
                    f'{structure} mask saved '
                )

            # ======================================================
            # Report what happened
            # ======================================================

            if any(save_structure.values()):

                print(
                    f'{pid}_{study_type}: Save completed.'
                )

            else:

                print(
                    f'{pid}_{study_type}: Nothing was saved.'
                )

        # ==========================================================
        # Add assignment widget
        # ==========================================================

        viewer.window.add_dock_widget(
            cortex_medulla_assignment,
            area='right'
        )

        # ==========================================================
        # Add nnInteractive
        # ==========================================================

        viewer.window.add_plugin_dock_widget(
            'napari-nninteractive'
        )

        # ==========================================================
        # Install close warning
        # ==========================================================

        close_filter = CloseWarningFilter(
            viewer,
            pid,
            saved_lkc,
            saved_lkm,
            saved_rkc,
            saved_rkm,
            finished
        )

        viewer.window._qt_window.installEventFilter(
            close_filter
        )

        # Keep a reference attached to the window so the filter
        # cannot be garbage-collected while Napari is running.
        viewer.window._qt_window._close_warning_filter = (
            close_filter
        )

        # ==========================================================
        # Run viewer
        # ==========================================================

        napari.run()

        # ==========================================================
        # Viewer has now actually closed
        # ==========================================================

        if not finished['value']:

            print(
                f'{pid}_{study_type}: Viewer closed without processing.'
            )

        else:

            print(
                f'{pid}_{study_type}: Case closed.'
            )
        # ----------------------------------------------------------
        # Stop after requested case
        # ----------------------------------------------------------

        if case_id:
            break


if __name__ == '__main__':

    draw_cortex_medulla(
        'Patients',
        'Leeds'
    )