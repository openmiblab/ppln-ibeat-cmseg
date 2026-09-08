# Manual cortex-medulla segmentation in iBEAt

# Stages

- stage_1_download: Download T1-weighted images from XNAT (use template from dixon clean).
- stage_2_data_harmonization: Clean up folder structure and series descriptions to create a clean dicom database (use template from dixon clean).
- stage_3_manual_segmentation: loop through the cases, pop up nninteractive for each case, and save the segmentations as DICOM (use template from ppln-ibeat-totseg stage_4_edit)
- stage_4_display: build mosaics showing the segmentations on top of the T1-weighted images for checking (use template from  ppln-ibeat-totseg)
- stage_5_measure: extract shape metrics from cortex masks (use template from  ppln-ibeat-totseg).

