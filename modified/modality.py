import os
import shutil
from typing import List, Optional

from auxiliary.nifti.io import read_nifti, write_nifti
from auxiliary.normalization.normalizer_base import Normalizer
from auxiliary.turbopath import turbopath

from brainles_preprocessing.brain_extraction.brain_extractor import BrainExtractor
from brainles_preprocessing.registration.registrator import Registrator


class ModifiedModalitiy:
    """
    Represents a medical image modality with associated preprocessing information.

    Args:
        modality_name (str): Name of the modality, e.g., "T1", "T2", "FLAIR".
        image_path (str): Path to the input modality data.
        output_path (str): Path to save the preprocessed modality data.
        bet (bool): Indicates whether brain extraction should be performed (True) or not (False).
        normalizer (Normalizer, optional): An optional normalizer for intensity normalization.

    Attributes:
        modality_name (str): Name of the modality.
        image_path (str): Path to the input modality data.
        output_path (str): Path to save the preprocessed modality data.
        bet (bool): Indicates whether brain extraction is enabled.
        normalizer (Normalizer, optional): An optional normalizer for intensity normalization.

    Example:
        >>> t1_modality = ModifiedModalitiy(
        ...     modality_name="T1",
        ...     image_path="/path/to/input_t1.nii",
        ...     output_path="/path/to/preprocessed_t1.nii",
        ...     bet=True
        ... )

    """

    def __init__(
        self,
        modality_name: str,
        image_path: str, # center or moving file
        roi_path: Optional[str] = None, # roi file, can be None
        biopsy_path: Optional[str] = None,
        raw_bet_output_path: Optional[str] = None,
        raw_bet_output_path_roi: Optional[str] = None,
        raw_skull_output_path: Optional[str] = None,
        raw_skull_output_path_roi: Optional[str] = None,
        normalized_bet_output_path: Optional[str] = None,
        normalized_bet_output_path_roi: Optional[str] = None,
        normalized_skull_output_path: Optional[str] = None,
        normalized_skull_output_path_roi: Optional[str] = None,
        normalizer: Optional[Normalizer] = None,
        atlas_correction: bool = True,
    ) -> None:
        # basics
        self.modality_name = modality_name

        self.image_path = turbopath(image_path)
        self.roi_path = turbopath(roi_path) if roi_path is not None else None
        self.biopsy_path = turbopath(biopsy_path) if biopsy_path is not None else None

        self.roi_name = f'{self.modality_name}_roi' if self.roi_path is not None else None
        self.biopsy_name = f'{self.modality_name}_biopsy' if self.biopsy_path is not None else None

        self.current_image = self.image_path
        self.current_roi = self.roi_path
        self.current_biopsy = self.biopsy_path

        self.normalizer = normalizer
        self.atlas_correction = atlas_correction

        # check that atleast one output is generated
        if (
            raw_bet_output_path is None
            and normalized_bet_output_path is None
            and raw_skull_output_path is None
            and normalized_skull_output_path is None
        ):
            raise ValueError(
                "All output paths are None. At least one output path must be provided."
            )

        # handle input paths
        if raw_bet_output_path is not None:
            self.raw_bet_output_path = turbopath(raw_bet_output_path)
            self.raw_bet_output_path_roi = turbopath(raw_bet_output_path_roi)
        else:
            self.raw_bet_output_path = raw_bet_output_path
            self.raw_bet_output_path_roi = raw_bet_output_path_roi

        if raw_skull_output_path is not None:
            self.raw_skull_output_path = turbopath(raw_skull_output_path)
            self.raw_skull_output_path_roi = turbopath(raw_skull_output_path_roi)
        else:
            self.raw_skull_output_path = raw_skull_output_path
            self.raw_skull_output_path_roi = raw_skull_output_path_roi

        if normalized_bet_output_path is not None:
            if normalizer is None:
                raise ValueError(
                    "A normalizer must be provided if normalized_bet_output_path is not None."
                )
            self.normalized_bet_output_path = turbopath(normalized_bet_output_path)
            self.normalized_bet_output_path_roi = turbopath(normalized_bet_output_path_roi)
        else:
            self.normalized_bet_output_path = normalized_bet_output_path
            self.normalized_bet_output_path_roi = normalized_bet_output_path_roi

        if normalized_skull_output_path is not None:
            if normalizer is None:
                raise ValueError(
                    "A normalizer must be provided if normalized_skull_output_path is not None."
                )
            self.normalized_skull_output_path = turbopath(normalized_skull_output_path)
            self.normalized_skull_output_path_roi = turbopath(normalized_skull_output_path_roi)
        else:
            self.normalized_skull_output_path = normalized_skull_output_path
            self.normalized_skull_output_path_roi = normalized_skull_output_path_roi

    @property
    def bet(self) -> bool:
        return any(
            path is not None
            for path in [self.raw_bet_output_path, self.normalized_bet_output_path]
        )

    def normalize(
        self,
        temporary_directory: str,
        store_unnormalized: str | None = None,
    ) -> None:
        """
        Normalize the image using the specified normalizer.

        Args:
            temporary_directory (str): Path to the temporary directory.
            store_unnormalized (str, optional): Path to store unnormalized images.

        Returns:
            None
        """
        # Backup the unnormalized file
        if store_unnormalized is not None:
            os.makedirs(store_unnormalized, exist_ok=True)
            shutil.copyfile(
                src=self.current_image,
                dst=f"{store_unnormalized}/unnormalized__{self.modality_name}.nii.gz",
            )

        if temporary_directory is not None:
            unnormalized_dir = f"{temporary_directory}/unnormalized"
            os.makedirs(unnormalized_dir, exist_ok=True)
            shutil.copyfile(
                src=self.current_image,
                dst=f"{unnormalized_dir}/unnormalized__{self.modality_name}.nii.gz",
            )

        # Normalize the image
        if self.normalizer is not None:
            image = read_nifti(self.current_image)
            normalized_image = self.normalizer.normalize(image=image)
            write_nifti(
                input_array=normalized_image,
                output_nifti_path=self.current_image,
                reference_nifti_path=self.current_image,
            )

    def register(
        self,
        registrator: Registrator,
        fixed_image_path: str,
        registration_dir: str,
        moving_image_name: str,
    ) -> str:
        """
        Register the current modality to a fixed image using the specified registrator.

        Args:
            registrator (Registrator): The registrator object.
            fixed_image_path (str): Path to the fixed image.
            registration_dir (str): Directory to store registration results.
            moving_image_name (str): Name of the moving image.

        Returns:
            str: Path to the registration matrix.
        """
        registered = os.path.join(registration_dir, f"{moving_image_name}.nii.gz")
        registered_matrix = os.path.join(
            registration_dir, f"{moving_image_name}"
        )  # note, add file ending depending on registration backend!
        registered_log = os.path.join(registration_dir, f"{moving_image_name}.log")

        registrator.register(
            fixed_image_path=fixed_image_path,
            moving_image_path=self.current_image,
            transformed_image_path=registered,
            matrix_path=registered_matrix,
            log_file_path=registered_log,
        )

        self.current_image = registered
        return registered_matrix

    def apply_mask(
        self,
        brain_extractor: BrainExtractor,
        brain_masked_dir_path: str,
        atlas_mask_path: str,
    ) -> None:
        """
        Apply a brain mask to the current modality using the specified brain extractor.

        Args:
            brain_extractor (BrainExtractor): The brain extractor object.
            brain_masked_dir_path (str): Directory to store masked images.
            atlas_mask_path (str): Path to the brain mask.

        Returns:
            None
        """
        if self.bet:
            brain_masked = os.path.join(
                brain_masked_dir_path,
                f"brain_masked__{self.modality_name}.nii.gz",
            )
            brain_extractor.apply_mask(
                input_image_path=self.current_image,
                mask_image_path=atlas_mask_path,
                masked_image_path=brain_masked,
            )
            self.current_image = brain_masked

    def transform(
        self,
        registrator: Registrator,
        fixed_image_path: str,
        registration_dir_path: str,
        moving_image_name: str,
        transformation_matrix_path: str,
    ) -> None:
        """
        Transform the current modality using the specified registrator and transformation matrix.

        Args:
            registrator (Registrator): The registrator object.
            fixed_image_path (str): Path to the fixed image.
            registration_dir_path (str): Directory to store transformation results.
            moving_image_name (str): Name of the moving image.
            transformation_matrix_path (str): Path to the transformation matrix.

        Returns:
            None
        """
        transformed = os.path.join(registration_dir_path, f"{moving_image_name}.nii.gz")
        transformed_log = os.path.join(
            registration_dir_path, f"{moving_image_name}.log"
        )

        registrator.transform(
            fixed_image_path=fixed_image_path,
            moving_image_path=self.current_image,
            transformed_image_path=transformed,
            matrix_path=transformation_matrix_path,
            log_file_path=transformed_log,
        )
        self.current_image = transformed

    def transform_binary(
            self,
            registrator: Registrator,
            fixed_image_path: str,
            registration_dir_path: str,
            moving_binary_name: str,
            transformation_matrix_path: str,
            binary_type: str
    ) -> None:
        """
        Transform the current modality using the specified registrator and transformation matrix.

        Args:
            registrator (Registrator): The registrator object.
            fixed_image_path (str): Path to the fixed image.
            registration_dir_path (str): Directory to store transformation results.
            moving_binary_name (str): Name of the moving image.
            transformation_matrix_path (str): Path to the transformation matrix.
            binary_type (str): Type of the binary mask: roi or biopsy

        Returns:
            None
        """

        assert binary_type in ["roi", "biopsy"]

        transformed = os.path.join(registration_dir_path, f"{moving_binary_name}.nii.gz")
        transformed_log = os.path.join(
            registration_dir_path, f"{moving_binary_name}.log"
        )

        if binary_type == "roi":
            registrator.transform(
                fixed_image_path=fixed_image_path,
                moving_image_path=self.current_roi,
                transformed_image_path=transformed,
                matrix_path=transformation_matrix_path,
                log_file_path=transformed_log,
                is_binary=True, # currently implemented for ANTs registrator only
            )
            self.current_roi = transformed
        elif binary_type == "biopsy":
            registrator.transform(
                fixed_image_path=fixed_image_path,
                moving_image_path=self.current_biopsy,
                transformed_image_path=transformed,
                matrix_path=transformation_matrix_path,
                log_file_path=transformed_log,
                is_binary=True,  # currently implemented for ANTs registrator only
            )
            self.current_biopsy = transformed
        else:
            raise ValueError(f"binary_type {binary_type} not supported")

    def extract_brain_region(
        self,
        brain_extractor: BrainExtractor,
        bet_dir_path: str,
    ) -> str:
        """
        Extract the brain region using the specified brain extractor.

        Args:
            brain_extractor (BrainExtractor): The brain extractor object.
            bet_dir_path (str): Directory to store brain extraction results.

        Returns:
            str: Path to the extracted brain mask.
        """
        bet_log = os.path.join(bet_dir_path, "brain-extraction.log")
        atlas_bet_cm = os.path.join(
            bet_dir_path, f"atlas_bet_{self.modality_name}.nii.gz"
        )
        atlas_mask_path = os.path.join(
            bet_dir_path, f"atlas_bet_{self.modality_name}_mask.nii.gz"
        )

        brain_extractor.extract(
            input_image_path=self.current_image,
            masked_image_path=atlas_bet_cm,
            brain_mask_path=atlas_mask_path,
            log_file_path=bet_log,
        )
        if self.bet is True:
            self.current_image = atlas_bet_cm
        return atlas_mask_path

    def save_current_image(
        self,
        output_path: str,
        normalization=False,
    ) -> None:
        os.makedirs(output_path.parent, exist_ok=True)

        if normalization is False:
            shutil.copyfile(
                self.current_image,
                output_path,
            )
        elif normalization is True:
            image = read_nifti(self.current_image)
            print("current image", self.current_image)
            normalized_image = self.normalizer.normalize(image=image)
            write_nifti(
                input_array=normalized_image,
                output_nifti_path=output_path,
                reference_nifti_path=self.current_image,
            )

    def save_current_binary(
        self,
        output_path: str,
        normalization=False,
        binary_type: str = "roi",
    ) -> None:

        assert binary_type in ["roi", "biopsy"]
        os.makedirs(output_path.parent, exist_ok=True)
        if binary_type == "roi":
            current_file = self.current_roi
        elif binary_type == "biopsy":
            current_file = self.current_biopsy
        else:
            raise ValueError

        if normalization is False:
            shutil.copyfile(
                current_file,
                output_path,
            )
        elif normalization is True:
            image = read_nifti(current_file)
            print("current image", current_file)
            # normalized_image = self.normalizer.normalize(image=image)
            write_nifti(
                input_array=image,
                output_nifti_path=output_path,
                reference_nifti_path=current_file,
            )
