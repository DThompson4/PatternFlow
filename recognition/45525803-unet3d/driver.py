import tensorflow as tf

import numpy as np
import nibabel as nib
import glob
import matplotlib.pyplot as plt
import os

from pyimgaug3d.augmentation import GridWarp, Flip, Identity
from pyimgaug3d.augmenters import ImageSegmentationAugmenter
from pyimgaug3d.utils import to_channels

MRI_PATH = '/home/Student/s4552580/mri_data/semantic_MRs_anon/'
LABEL_PATH = '/home/Student/s4552580/mri_data/semantic_labels_anon/'

PROCESSED_MRI_PATH = '/home/Student/s4552580/mri_data/processed_mri'
PROCESSED_LABEL_PATH = '/home/Student/s4552580/mri_data/processed_label'

TRAIN_CASE_NUMBERS = range(4,30)
TEST_CASE_NUMBERS = range(30,43)
N_CLASSES = 6

MISMATCHED_SHAPE_NAME = 'Case_019_Week1'

def get_case_weeks(mri_path, case_numbers):
    
    case_weeks = []
    
    for case_number in case_numbers:
        
        full_filenames = glob.glob(f'{mri_path}{os.sep}Case_{case_number:03}*')
        for full_filename in full_filenames:
            
            filename = full_filename.split(f'{os.sep}')[-1]
            case_week = '_'.join(filename.split('_')[0:3])
            if case_week != MISMATCHED_SHAPE_NAME:
                case_weeks.append(case_week)
            
    return case_weeks

def load_mri_label(case_week):
    
    mri_filename = f'{MRI_PATH}{os.sep}{case_week}_LFOV.nii.gz'
    label_filename = f'{LABEL_PATH}{os.sep}{case_week}_SEMANTIC_LFOV.nii.gz'
    
    mri = nib.load(mri_filename).get_fdata()
    label = nib.load(label_filename).get_fdata()
    
    return mri, label

def save_nifti(data, folder, filename, affine=np.eye(4)):
    
    img = nib.Nifti1Image(data, affine)
    if not os.path.exists(folder):
        os.mkdir(folder)
    nib.save(img, os.path.join(folder, filename))

def write_original_and_augmented(case_weeks, num_augs=3):
    
    mri_filenames = []
    label_filenames = []
    
    for case_week in case_weeks:
    
        mri, label = load_mri_label(case_week)
        mri_extra_dim = mri[..., None]
        seg = to_channels(label)

        mri_filename = f'{case_week}_MRI_ORIGINAL.nii.gz'
        label_filename = f'{case_week}_LABEL_ORIGINAL.nii.gz'

        mri_filenames.append(mri_filename)
        label_filenames.append(label_filename)

        save_nifti(mri, PROCESSED_MRI_PATH, mri_filename)
        save_nifti(label, PROCESSED_LABEL_PATH, label_filename)

        for i in range(num_augs):

            aug = ImageSegmentationAugmenter()
            aug.add_augmentation(GridWarp(grid=(4, 4, 4), max_shift=5))
            
            aug_mri, aug_seg = aug([mri_extra_dim, seg])
            aug_mri = aug_mri[:,:,:,0]

            aug_label = np.argmax(aug_seg, axis=-1).astype('int16')

            mri_filename = f'{case_week}_MRI_AUG{i+1}.nii.gz'
            label_filename = f'{case_week}_LABEL_AUG{i+1}.nii.gz'

            mri_filenames.append(mri_filename)
            label_filenames.append(label_filename)

            save_nifti(aug_mri.numpy().astype('float64'), PROCESSED_MRI_PATH, mri_filename)
            save_nifti(aug_label, PROCESSED_LABEL_PATH, label_filename)

        print(f'{case_week} written')

    return mri_filenames, label_filenames