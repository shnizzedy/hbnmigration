"""Transfer data from Ripple to REDCap."""

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
import requests

from .._config_variables import redcap_variables, ripple_variables
from ..exceptions import NoData
from ..utility_functions import initialize_logging, yesterday

initialize_logging()
logger = logging.getLogger(__name__)


@dataclass
class Endpoints:
    """API Endpoints."""

    REDCap = redcap_variables.Endpoints()
    """REDCap API endpoints."""
    Ripple = ripple_variables.Endpoints()
    """Riplle API endpoints."""


def request_potential_participants() -> pd.DataFrame:
    """Request Ripple potential participants data via Ripple API Export."""
    ripple_df = pd.concat(
        [
            ripple_variables.export_from_ripple(
                ripple_study,
                {
                    "surveyExportSince": yesterday,
                    **ripple_variables.column_dict(
                        [
                            "globalId",
                            "firstName",
                            "middleName",
                            "lastName",
                            "sex",
                            "birthday",
                            "race",
                            "ethnicity",
                            "contactForFutureStudies",
                            "familyId",
                            "tags",
                            "dateCreated",
                            "statusId",
                            "customId",
                            "signedConsentForm",
                            "dateSignedConsentForm",
                            "age",
                            "lastContactDate",
                            "strategyId",
                            "sourceId",
                            "siteId",
                            "dateAddedToStudy",
                            "cv.desired_result_of_evaluation",
                            "cv.referral_source_description",
                            "cv.hx_of_lifetime_substance_dependence",
                            "cv.referral_source_rt",
                            "cv.substance_dependence_info",
                            "cv.substance_dependence",
                            "cv.preferred_scan_site",
                            "cv.hbn_enrollment_site",
                            "cv.participant_track",
                            "cv.consent_form",
                            "Participant Contacts",
                        ]
                    ),
                },
            )
            for ripple_study in [
                v
                for k, v in ripple_variables.study_ids.items()
                if k in ["HBN - Main", "HBN - Waitlist"]
            ]
        ]
    )
    row_count = ripple_df.shape[0]
    logging.info("Ripple Returned Rows: %s", row_count)
    # Check if the returned DataFrame is empty to infer the API status.
    if ripple_df.empty:
        # If the DataFrame is empty, the API call may have failed or returned no data.
        logging.info("API request returned no data.")
        raise NoData
    # Filter the dataFrame on cv.consent_form and contact.2.infos.1.contactType
    # filtered_ripple_df = ripple_df[ripple_df['cv.consent_form'] == 'Send to RedCap']
    filtered_ripple_df = ripple_df[(ripple_df["cv.consent_form"] == "Send to RedCap")]
    if filtered_ripple_df.empty:
        # If the DataFrame is empty, the API call may have failed or returned no data.
        logging.info('There are no participants marked "Send to RedCap".')
        raise NoData
    row_count = filtered_ripple_df.shape[0]
    logging.info(
        "API request successful and data received.\nRipple Filtered Rows: %s", row_count
    )
    return filtered_ripple_df


def set_redcap_columns(
    ripple_df: pd.DataFrame,
    columns_to_keep: list[str] = ["mrn", "email_consent"],
    columns_to_rename: dict = {"customId": "mrn"},
) -> pd.DataFrame:
    """
    Set appropriate columns.

    Define the columns you want to select:
    Ripple globalId, customId (MRN), contact.*.infos.*.information (contact email).
    Create a new dataframe with only the selected columns.
    """
    # Before renaming columns copy dataframe to create an independent DataFrame
    redcap_df = ripple_df.copy()

    contact_type_cols = [
        col for col in redcap_df.columns if col.endswith(".contactType")
    ]
    for col in contact_type_cols:
        col.replace(".contactType", ".information")

    # Create masks
    is_email = redcap_df[contact_type_cols] == "email"

    # Get first occurrence index per row
    first_match = is_email.idxmax(axis=1)

    # Get corresponding information
    redcap_df["email_consent"] = redcap_df.apply(
        lambda row: (
            row[first_match[row.name].replace(".contactType", ".information")]
            if is_email.loc[row.name].any()
            else np.nan
        ),
        axis=1,
    )
    redcap_df.rename(columns=columns_to_rename, inplace=True)
    # Convert MRN to integer
    redcap_df["mrn"] = redcap_df["mrn"].astype(int)

    # Autonumber
    redcap_df["forceAutoNumber"] = True

    return redcap_df[columns_to_keep].drop_duplicates()


def prepare_redcap_data(df: pd.DataFrame) -> None:
    """Prepare Ripple API returned data to be imported into REDCap."""
    copy_selected_redcap_df = set_redcap_columns(df)

    # Save the new dataframe to a CSV file
    copy_selected_redcap_df.to_csv(redcap_variables.redcap_import_file, index=False)


def prepare_ripple_to_ripple(df: pd.DataFrame) -> dict[str, str]:
    """Prepare Ripple API returned data to be re-imported (updated) in Ripple."""
    ripple_import_files: dict[str, str] = {}

    # Define the columns you want to select
    columns_to_keep_ripple = ["globalId", "cv.consent_form", "importType"]

    # Create a new dataframe with only the selected columns
    selected_ripple_df = df[columns_to_keep_ripple]

    for ripple_study in selected_ripple_df["importType"].unique():
        # Before updating column the cv.consent_form value
        # copy dataframe to create an independent DataFrame
        copy_selected_ripple_df = selected_ripple_df.copy()

        # Filter down to relevant rows
        copy_selected_ripple_df = copy_selected_ripple_df[
            copy_selected_ripple_df["importType"] == ripple_study
        ]
        copy_selected_ripple_df["cv.consent_form"] = "consent_form_created_in_redcap"

        ripple_import_dir = Path(ripple_variables.ripple_import_file).parent
        ripple_import_filepath = str(ripple_import_dir / f"{ripple_study}.xlsx")
        # Save the new dataframe to a Excel file
        copy_selected_ripple_df.to_excel(
            ripple_import_filepath, index=False, sheet_name="SentToRedCap"
        )
        ripple_import_files[ripple_study] = ripple_import_filepath
    return ripple_import_files


def push_to_redcap(project_token: str) -> None:
    """Push the HBN Potential Participants MRN and Contact email to RedCap."""
    # Read the content of the CSV file
    try:
        with open(redcap_variables.redcap_import_file, "r") as file:
            csv_content = file.read()
    except FileNotFoundError:
        logger.exception(
            "Error: The file '%s' was not found.", redcap_variables.redcap_import_file
        )
        # You might want to create a placeholder or exit
        csv_content = ""  # Default to empty string if file not found
    if csv_content:
        data = {
            "token": project_token,
            "content": "record",
            "action": "import",
            "format": "csv",
            "type": "flat",
            "overwriteBehavior": "normal",
            "forceAutoNumber": "false",
            "data": csv_content,
            "returnContent": "count",
            "returnFormat": "csv",
        }

        r = requests.post(Endpoints.REDCap.base_url, data=data)

        logging.info("HTTP Status: %s\nRecords Inserted: %s", r.status_code, r.text)


def set_status_in_ripple(ripple_study: str, ripple_import_file: str) -> None:
    """
    Set the HBN Potential Participants consent form flag status.

    In **Consent Form Created in RedCap** in Ripple after RedCap Consent data push.
    """
    try:
        # Read the Excel file into a pandas DataFrame first to check its contents
        df = pd.read_excel(ripple_import_file)

        # Check if the DataFrame is not empty
        if df.empty:
            logging.info(
                "The Excel file %s is empty. No API request was sent.",
                ripple_import_file,
            )
            return
        logging.info("File contains data. Proceeding with API request…")
        study_import_url = Endpoints.Ripple.import_data(ripple_study)
        with open(ripple_import_file, "rb") as ripple_file:
            file_content = ripple_file.read()
            response = requests.post(
                study_import_url,
                headers=ripple_variables.headers["import"],
                data=file_content,
            )
            try:
                # Raise an exception for bad status codes (4xx or 5xx)
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                logging.debug(study_import_url)
                logging.debug(file_content)
                raise
            logging.info("Request was successful!\nResponse: %s", response.text)
    except FileNotFoundError as e:
        msg = f"Error: The file '{ripple_import_file}' was not found."
        raise FileNotFoundError(msg) from e
    except requests.exceptions.RequestException as e:
        # This will catch network-related errors like connection errors, timeouts, etc.
        msg = f"An error occurred during the API request: {e}"
        raise requests.exceptions.RequestException(msg) from e
    except Exception as e:
        # A general exception for other potential errors
        # (e.g., file is not a valid Excel file)
        logging.exception("An unexpected error occurred: %s", e)  # noqa: TRY401
        raise


def cleanup() -> None:
    """Delete temporary files."""
    for filepath in [
        redcap_variables.redcap_import_file,
        ripple_variables.ripple_import_file,
    ]:
        try:
            filepath.unlink(missing_ok=True)
        except FileNotFoundError:
            logger.warning("%s already does not exist.", filepath)


def main(project_status: Literal["dev", "prod"] = "dev") -> None:
    """Transfer data from Ripple to REDCap."""
    project = {
        "dev": {"token": redcap_variables.Tokens.pid757},
        "prod": {"token": redcap_variables.Tokens.pid247},
    }
    try:
        filtered_ripple_df = request_potential_participants()
        prepare_redcap_data(filtered_ripple_df)
        ripple_import_files = prepare_ripple_to_ripple(filtered_ripple_df)
        push_to_redcap(project[project_status]["token"])
        for ripple_study, ripple_import_file in ripple_import_files.items():
            set_status_in_ripple(ripple_study, ripple_import_file)
    except NoData:
        pass
    finally:
        cleanup()


if __name__ == "__main__":
    main(project_status="dev")
