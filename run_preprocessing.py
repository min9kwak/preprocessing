import argparse
from auxiliary.normalization.percentile_normalizer import PercentileNormalizer
from auxiliary.turbopath import turbopath
from tqdm import tqdm

from brainles_preprocessing.brain_extraction import HDBetExtractor
from modified.modality import ModifiedModalitiy
from modified.preprocessor import ModifiedPreprocessor
# from brainles_preprocessing.registration import ANTsRegistrator
from modified.ANTs import ModifiedANTsRegistrator


def preprocess_exam_in_brats_style(args: argparse.Namespace, input_dir: str) -> None:
    """
    Perform BRATS (Brain Tumor Segmentation) style preprocessing on MRI exam data.

    Args:
        args (argparse.Namespace): Command line arguments.
        input_dir (str): Path to the directory containing raw MRI files for an exam.

    Raises:
        Exception: If any error occurs during the preprocessing.

    Example:
        brat_style_preprocess_exam("/path/to/exam_directory")

    This function preprocesses MRI exam data following the BRATS style, which includes the following steps:
    1. Normalization using a percentile normalizer.
    2. Registration and correction using NiftyReg.
    3. Brain extraction using HDBet.

    The processed data is saved in a structured directory within the input directory.

    Args:
        input_dir (str): Path to the directory containing raw MRI files for an exam.

    Returns:
        None
    """
    input_dir = turbopath(input_dir)
    print("*** start ***")
    brainles_dir = turbopath(input_dir) + "/" + input_dir.name + "_brainles"

    raw_bet_dir = brainles_dir / "raw_bet" if args.return_raw else None
    norm_bet_dir = brainles_dir / "normalized_bet" if args.return_normalized else None
    if raw_bet_dir is None and norm_bet_dir is None:
        raise ValueError(
            "Both raw_bet_dir and norm_bet_dir cannot be None. Enable at least one of the options: "
            "return_raw or return_normalized."
        )

    modality_files = {
        "t1c": input_dir.files("*t1c.nii.gz"),
        "t2": input_dir.files("*t2.nii.gz"),
        "t1": input_dir.files("*t1.nii.gz"),
        "fla": input_dir.files("*fla.nii.gz")
    }

    roi_files = {
        "t1_roi": input_dir.files("*t1_roi.nii.gz"),
        "t2_roi": input_dir.files("*t2_roi.nii.gz"),
        "t1c_roi": input_dir.files("*t1c_roi.nii.gz"),
        "fla_roi": input_dir.files("*fla_roi.nii.gz")
    }

    biopsy_files = {
        "t1_biopsy": input_dir.files("*t1_biopsy.nii.gz"),
        "t2_biopsy": input_dir.files("*t2_biopsy.nii.gz"),
        "t1c_biopsy": input_dir.files("*t1c_biopsy.nii.gz"),
        "fla_biopsy": input_dir.files("*fla_biopsy.nii.gz")
    }

    # Select the center modality based on priority
    used_modalities = []
    center_modality = None
    for modality_name in ["t1c", "t2", "t1", "flair"]:
        if len(modality_files[modality_name]) == 1:
            center_modality = modality_name
            center_file = modality_files[modality_name][0]
            used_modalities.append(modality_name)
            break

    if center_modality is None:
        raise Exception("No suitable center modality found.")
    print(f"Center modality: {center_modality}")

    # Define the center modality
    percentile_normalizer = PercentileNormalizer(
        lower_percentile=0.1,
        upper_percentile=99.9,
        lower_limit=0,
        upper_limit=1,
    )

    if len(roi_files[f'{center_modality}_roi']) == 1:
        roi_path = roi_files[f'{center_modality}_roi'][0]
    else:
        roi_path = None

    if len(biopsy_files[f'{center_modality}_biopsy']) == 1:
        biopsy_path = biopsy_files[f'{center_modality}_biopsy'][0]
    else:
        biopsy_path = None

    center = ModifiedModalitiy(
        modality_name=center_modality,
        image_path=center_file,
        roi_path=roi_path,
        biopsy_path=biopsy_path,
        raw_bet_output_path=(raw_bet_dir / f"{input_dir.name}_{center_modality}_bet.nii.gz") if args.return_raw else None,
        raw_bet_output_path_roi=(raw_bet_dir / f"{input_dir.name}_{center_modality}_roi_bet.nii.gz") if args.return_raw else None,
        normalized_bet_output_path=(norm_bet_dir / f"{input_dir.name}_{center_modality}_bet.nii.gz") if args.return_normalized else None,
        normalized_bet_output_path_roi=(norm_bet_dir / f"{input_dir.name}_{center_modality}_roi_bet.nii.gz") if args.return_normalized else None,
        atlas_correction=True,
        normalizer=percentile_normalizer,
    )

    # Define the moving modalities
    moving_modalities = []
    for modality_name, files in modality_files.items():
        if modality_name != center_modality and len(files) == 1:

            # mri
            image_path = files[0]

            # roi
            if len(roi_files[f'{modality_name}_roi']) == 1:
                roi_path = roi_files[f'{modality_name}_roi'][0]
            else:
                roi_path = None

            # biopsy
            if len(biopsy_files[f'{modality_name}_biopsy']) == 1:
                biopsy_path = biopsy_files[f'{modality_name}_biopsy'][0]
            else:
                biopsy_path = None

            moving_modalities.append(
                ModifiedModalitiy(
                    modality_name=modality_name,
                    image_path=image_path,
                    roi_path=roi_path,
                    biopsy_path=biopsy_path,
                    raw_bet_output_path=(raw_bet_dir / f"{input_dir.name}_{modality_name}_bet.nii.gz") if args.return_raw else None,
                    raw_bet_output_path_roi=(raw_bet_dir / f"{input_dir.name}_{modality_name}_roi_bet.nii.gz") if args.return_raw else None,
                    normalized_bet_output_path=(norm_bet_dir / f"{input_dir.name}_{modality_name}_bet.nii.gz") if args.return_normalized else None,
                    normalized_bet_output_path_roi=(norm_bet_dir / f"{input_dir.name}_{modality_name}_roi_bet.nii.gz") if args.return_normalized else None,
                    atlas_correction=True,
                    normalizer=percentile_normalizer,
                )
            )

    preprocessor = ModifiedPreprocessor(
        center_modality=center,
        moving_modalities=moving_modalities,
        registrator=ModifiedANTsRegistrator(threshold=args.threshold),
        brain_extractor=HDBetExtractor(),
        temp_folder="temporary_directory",
        limit_cuda_visible_devices="0",
    )

    preprocessor.run(
        save_dir_coregistration=brainles_dir + "/co-registration",
        save_dir_atlas_registration=brainles_dir + "/atlas-registration",
        save_dir_atlas_correction=brainles_dir + "/atlas-correction",
        save_dir_brain_extraction=brainles_dir + "/brain-extraction",
    )


def main():

    from utils.util import str2bool

    parser = argparse.ArgumentParser(description="Preprocess MRI exam data in BraTS style.")
    parser.add_argument('--data_dir', type=str, default="E:/data/GBM/data")
    parser.add_argument('--return_raw', type=str2bool, default=False)
    parser.add_argument('--return_normalized', type=str2bool, default=True)
    parser.add_argument('--threshold', type=float, default=0.5, help='ROI post-processing threshold')

    args = parser.parse_args()

    input_dirs = sorted(turbopath(args.data_dir).dirs())

    for input_dir in tqdm(input_dirs):
        print("processing:", input_dir)
        preprocess_exam_in_brats_style(args=args, input_dir=input_dir)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
