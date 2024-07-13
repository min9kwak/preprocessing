[![PyPI version preprocessing](https://badge.fury.io/py/brainles-preprocessing.svg)](https://pypi.python.org/pypi/brainles-preprocessing/)
[![Documentation Status](https://readthedocs.org/projects/brainles-preprocessing/badge/?version=latest)](http://brainles-preprocessing.readthedocs.io/?badge=latest)
[![tests](https://github.com/BrainLesion/preprocessing/actions/workflows/tests.yml/badge.svg)](https://github.com/BrainLesion/preprocessing/actions/workflows/tests.yml)


# Modified BrainLes-Preprocessing
This repository is a modified version of the original [BrainLes preprocessing](https://github.com/BrainLesion/preprocessing) tool (version 0.1.5).
[BrainLes preprocessing](https://github.com/BrainLesion/preprocessing) is a comprehensive tool for preprocessing tasks in biomedical imaging, with a focus on (but not limited to) multi-modal brain MRI.
BrainLes is written `backend-agnostic`, meaning it allows for swapping the registration and brain extraction tools.
It can be used to build modular preprocessing pipelines.

This includes the following steps:
1. **Co-registration**
2. **Atlas Registration**
3. **Atlas Correction** (optional, but enabled by default)
4. **Skull Stripping / Brain Extraction**
5. **Normalization** (scaling from 0 to 1; optional, but enabled by default)


## Requirements
### Installation
To use this package safely, ensure you have the following:
* Python 3.10+ environment
* Docker
* Linux
  * According to the original developers, Windows and Mac OS will be supported in future versions
* CUDA (optional, but recommended)

With a Python 3.10+ environment you can install directly from [pypi.org](https://pypi.org/project/brainles-preprocessing/):
```
pip install brainles-preprocessing auxiliary
```

### Registrator
To use the default registrator, ANTs, you need to install it with the following command:
 ```
pip install brainles_preprocessing[ants]
```
ANTs utilizes the `t1_brats_space.nii` located in the `registration/atlas` directory of the `BrainLes preprocessing`.
These files need to be moved to the main directory of your project.
For example, `Project_Root/registration/atlas/t1_brats_space.nii`.

***Note: the current implementation only supports ANTs.


## Modifications
The modified implementations (`modality.py`, `ANTs.py`, and `preprocessor.py`) locate in `modified` directory.


### 1. modality.py
The `modality.py` file provides the `ModifiedModality` class, which can handle MRI images, ROI 
(Region of Interest; binary values of 0 and 1) masks, and biopsy (binary pixels, not region) masks.
MRI images are either registered to a specific space (for center modality) or transformed (for moving modality) during each preprocessing step.
Correspondingly, the ROI and biopsy undergo an identical transformation as the MRI using `transform_binary`, ensuring it is mapped to the same space.


### 2. ANTs.py
The `ANTs.py` file provides the `ModifiedANTsRegistrator` class, which extends the functionality of the 
existing `ANTsRegistrator` to effectively handle ROI transformations. 
When transforming the ROI or biopsy, any values greater than **args.threshold** are converted to **1** to maintain the ROI or biopsy as a binary mask. 
This step is crucial because, without it, the affine transformation process could result in blurred edges of the 
final ROI or biopsy. By ensuring values remain binary, the integrity of the ROI or biopsy is preserved.


### 3. preprocessor.py
The `modified_preprocessor.py` file provides the `ModifiedPreprocessor` class, which performs the complete 
preprocessing steps. MRI images undergo *all five steps*, while ROI / biopsy masks only go through *the first three steps*. 
The steps are as follows:
1. **Co-registration**: This step adjusts the MRIs and ROIs / biopsies to match a predefined center modality (orientation and central point).
The center MRI is processed using the `register` function, while the center ROI / biopsy and moving MRI / ROI / biopsy are 
adjusted using the `transform` or `transform_binary` function to align with it.
2. **Atlas Registration**: This step adjusts the images to match the ANTs atlas.
It ensures that the spacing, dimension, orientation, central point, and so on are consistent with the BraTS standard.
3. **Atlas Correction (optional)**: This optional step further corrects any slight misalignments that remain after the atlas registration to ensure better accuracy.
4. **Skull Stripping / Brain Extraction**: This step extracts only the brain portion by removing the skull. The ROI is not used in this step as it does not locate within the skull.
5. **Normalization (optional)**: This optional step scales the intensity of the extracted brain MRI to a range of 0 to 1.


### 4. run_preprocessing.py
This script performs preprocessing on all MRI and ROI files in the data folder and saves the results of each preprocessing step.
Refer to the [Data Folder Structure](#data-folder-structure) section for the file organization format.

The following modality images, ROIs, and biopsies are supported: t1 (T1), t2 (T2), t1c (T1Gd), fla (Flair).
The center modality is determined based on the following priority: t1c, t2, t1, fla.
The remaining modalities become moving modalities. Preprocessing is performed even if not all four modalities are present.
All MRI images available for each patient undergo transformation.
However, ROIs are only transformed if the corresponding MRI modality is present.

By using the following paths to create the `ModifiedModality` instance, you can obtain brain images that are not normalized:
* `raw_bet_output_path=raw_bet_dir / f"{inputDir.name}_{center_modality}bet.nii.gz"`
* `raw_bet_output_path_roi=raw_bet_dir / f"{inputDir.name}{center_modality}_roi_bet.nii.gz"`

This allows you to obtain both normalized and non-normalized versions of the brain images.


## Data Folder Structure
To ensure your project is organized and easy to navigate, follow this data folder structure:

```
Project_Root/
└── data/
    └── {patient_id}/        # Replace {patient_id} with the actual patient identifier
        ├── t1.nii.gz
        ├── t1_roi.nii.gz
        ├── t1_biopsy.nii.gz
        ├── t1c.nii.gz
        ├── t1c_roi.nii.gz
        ├── t1c_biopsy.nii.gz
        ├── t2.nii.gz
        ├── t2_roi.nii.gz
        ├── t2_biopsy.nii.gz
        ├── fla.nii.gz
        ├── fla_roi.nii.gz
        └── fla_biopsy.nii.gz
```

Note that the file extensions and names should follow the provided format.

## Usage
Please have a look at the original [Jupyter Notebook tutorials](https://github.com/BrainLesion/tutorials/tree/main/preprocessing) illustrating the usage of BrainLes preprocessing.
The modified version is implemented as [run_preprocessing.py](#4-run_preprocessingpy). To perform preprocessing, run the following command:
```
python run_preprocessing.py
```

## Results
The results of the preprocessing are saved in the `{patient_id}_brainles` folder under the data directory. 
Each subfolder contains intermediate images, transformation matrices (.mat), and log files (.log) for each preprocessing step. 
The final outputs are saved in the `normalized_bet` directory.
Additionally, a `log` folder is created under the `Project_Root`, containing overall log files for each `patient_id`.

```
Project_Root/
├── data/
│   └── {patient_id}/
│       └── {patient_id}_brainles/
│           ├── atlas-correction/
│           ├── atlas-registration/
│           ├── brain-extraction/
│           ├── co-registration/
│           └── normalized_bet/
└── log/
    └── {patient_id}.log
```

To compress only the final results, use the following command:
```
find . -type d -name normalized_bet -exec zip -r normalized_bet_archives.zip {} +
```


### Atlas Reference
We provide the SRI-24 atlas from this [publication](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2915788/).
However, custom atlases can be supplied.

### Brain extraction
We currently provide support for [HD-BET](https://github.com/MIC-DKFZ/HD-BET).

### Registration
We currently provide support for [ANTs](https://github.com/ANTsX/ANTs) (default), [Niftyreg](https://github.com/KCL-BMEIS/niftyreg) (Linux), eReg (experimental)

<!-- TODO mention defacing -->
