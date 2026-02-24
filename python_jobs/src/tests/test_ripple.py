"""Tests for Ripple sourced data migration."""

from unittest.mock import patch

import pandas as pd
import pytest
import requests

from hbnmigration.exceptions import NoData
from hbnmigration.from_ripple.to_redcap import (
    main,
    prepare_redcap_data,
    push_to_redcap,
    request_potential_participants,
    set_redcap_columns,
    set_status_in_ripple,
)

from .conftest import assert_cleanup_called, assert_valid_redcap_columns


class TestRequestPotentialParticipants:
    """Tests for request_potential_participants function."""

    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_successful_request_with_valid_data(
        self, mock_vars, mock_endpoints, sample_ripple_data
    ):
        """Test successful API request returns filtered DataFrame."""
        mock_vars.study_ids = {
            "HBN - Main": "main_study_id",
            "HBN - Waitlist": "waitlist_study_id",
        }
        mock_vars.column_dict.return_value = {}

        # Return only the rows for each specific study
        main_data = sample_ripple_data[
            sample_ripple_data["importType"] == "HBN - Main"
        ]  # 2 rows
        waitlist_data = sample_ripple_data[
            sample_ripple_data["importType"] == "HBN - Waitlist"
        ]  # 2 rows
        mock_endpoints.Ripple.export_from_ripple.side_effect = [
            main_data,
            waitlist_data,
        ]

        result = request_potential_participants()
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4  # 2 from Main + 2 from Waitlist
        assert all(result["cv.consent_form"] == "Send to RedCap")

    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_empty_dataframe_raises_no_data(self, mock_vars, mock_endpoints):
        """Test empty DataFrame raises NoData exception."""
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}
        mock_endpoints.Ripple.export_from_ripple.return_value = pd.DataFrame()

        with pytest.raises(NoData):
            request_potential_participants()

    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_no_send_to_redcap_raises_no_data(
        self, mock_vars, mock_endpoints, anton_arcane_corrupted_data
    ):
        """Test no 'Send to RedCap' records raises NoData."""
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}
        mock_endpoints.Ripple.export_from_ripple.return_value = (
            anton_arcane_corrupted_data
        )

        with pytest.raises(NoData):
            request_potential_participants()

    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_filters_consent_form_correctly(self, mock_vars, mock_endpoints):
        """Test filtering by consent form status."""
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}
        mock_df = pd.DataFrame(
            {
                "globalId": ["ST001", "AA001", "ANT001"],
                "firstName": ["Alec", "Abby", "Anton"],
                "cv.consent_form": ["Send to RedCap", "Send to RedCap", "Pending"],
                "customId": [1, 2, 3],
            }
        )
        mock_endpoints.Ripple.export_from_ripple.return_value = mock_df

        result = request_potential_participants()
        assert len(result) == 2
        assert "ANT001" not in result["globalId"].values

    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_multiple_studies_concatenation(self, mock_vars, mock_endpoints):
        """Test data from multiple studies is properly concatenated."""
        mock_vars.study_ids = {
            "HBN - Main": "main_study_id",
            "HBN - Waitlist": "waitlist_study_id",
        }
        mock_vars.column_dict.return_value = {}

        mock_df_main = pd.DataFrame(
            {
                "globalId": ["ST001"],
                "firstName": ["Alec"],
                "cv.consent_form": ["Send to RedCap"],
                "customId": [1],
            }
        )
        mock_df_waitlist = pd.DataFrame(
            {
                "globalId": ["AA001"],
                "firstName": ["Abby"],
                "cv.consent_form": ["Send to RedCap"],
                "customId": [2],
            }
        )
        mock_endpoints.Ripple.export_from_ripple.side_effect = [
            mock_df_main,
            mock_df_waitlist,
        ]

        result = request_potential_participants()
        assert len(result) == 2
        assert set(result["globalId"].values) == {"ST001", "AA001"}

    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_single_record_processing(self, mock_vars, mock_endpoints):
        """Test processing with exactly one record."""
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}
        mock_df = pd.DataFrame(
            {
                "globalId": ["SGL001"],
                "firstName": ["Single"],
                "cv.consent_form": ["Send to RedCap"],
                "customId": [1],
            }
        )
        mock_endpoints.Ripple.export_from_ripple.return_value = mock_df

        result = request_potential_participants()
        assert len(result) == 1


class TestSetRedcapColumns:
    """Tests for set_redcap_columns function."""

    def test_basic_column_renaming(self, swamp_thing_participant):
        """Test basic column renaming and selection."""
        result = set_redcap_columns(swamp_thing_participant)
        assert_valid_redcap_columns(result)
        assert result["record_id"].iloc[0] == 12345
        assert result["mrn"].iloc[0] == 12345

    def test_email_extraction_from_contacts(self):
        """Test email extraction from contact fields."""
        ripple_df = pd.DataFrame(
            {
                "customId": [67890],
                "globalId": ["AA001"],
                "contact.1.infos.1.contactType": ["phone"],
                "contact.1.infos.1.information": ["504-555-0101"],
                "contact.2.infos.1.contactType": ["email"],
                "contact.2.infos.1.information": ["abby.arcane@parliament.org"],
            }
        )
        result = set_redcap_columns(ripple_df)
        assert result["email_consent"].iloc[0] == "abby.arcane@parliament.org"

    def test_multiple_email_contacts_first_wins(self):
        """Test that when multiple emails exist, first one is selected."""
        ripple_df = pd.DataFrame(
            {
                "customId": [77001],
                "globalId": ["WOO001"],
                "firstName": ["Tefé"],
                "contact.1.infos.1.contactType": ["email"],
                "contact.1.infos.1.information": ["tefe.holland@swamp.com"],
                "contact.2.infos.1.contactType": ["email"],
                "contact.2.infos.1.information": ["tefe.alt@parliament.org"],
            }
        )
        result = set_redcap_columns(ripple_df)
        assert result["email_consent"].iloc[0] == "tefe.holland@swamp.com"

    def test_no_email_contact_results_in_nan(self):
        """Test that missing email results in NaN."""
        ripple_df = pd.DataFrame(
            {
                "customId": [66001],
                "globalId": ["SAU001"],
                "firstName": ["Sunderland"],
                "contact.1.infos.1.contactType": ["phone"],
                "contact.1.infos.1.information": ["504-555-0666"],
            }
        )
        result = set_redcap_columns(ripple_df)
        assert pd.isna(result["email_consent"].iloc[0])

    def test_unicode_characters_in_names(self):
        """Test handling of Unicode characters in participant names."""
        ripple_df = pd.DataFrame(
            {
                "customId": [77777],
                "globalId": ["UNI001"],
                "firstName": ["François"],
                "lastName": ["Müller-Göthe"],
                "contact.1.infos.1.contactType": ["email"],
                "contact.1.infos.1.information": ["françois@müller.com"],
            }
        )
        result = set_redcap_columns(ripple_df)
        assert result["record_id"].iloc[0] == 77777

    def test_empty_string_vs_none_handling(self):
        """Test distinction between empty strings and None values."""
        ripple_df = pd.DataFrame(
            {
                "customId": [66666, 66667],
                "globalId": ["EMP001", "EMP002"],
                "firstName": ["", None],
                "contact.1.infos.1.contactType": ["email", "email"],
                "contact.1.infos.1.information": ["", "none@test.com"],
            }
        )
        result = set_redcap_columns(ripple_df)
        assert len(result) == 2

    def test_contact_info_with_multiple_types(self):
        """Test extraction of email from mixed contact types."""
        ripple_df = pd.DataFrame(
            {
                "customId": [88888],
                "globalId": ["MCT001"],
                "firstName": ["MultiContact"],
                "contact.1.infos.1.contactType": ["phone"],
                "contact.1.infos.1.information": ["504-555-8888"],
                "contact.2.infos.1.contactType": ["email"],
                "contact.2.infos.1.information": ["multi@swamp.com"],
                "contact.3.infos.1.contactType": ["address"],
                "contact.3.infos.1.information": ["123 Swamp Lane"],
            }
        )
        result = set_redcap_columns(ripple_df)
        assert result["email_consent"].iloc[0] == "multi@swamp.com"


class TestPrepareRedcapData:
    """Tests for prepare_redcap_data function."""

    @patch("hbnmigration.from_ripple.to_redcap.set_redcap_columns")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_saves_csv_file(self, mock_vars, mock_set_columns, temp_csv_file):
        """Test that data is saved to CSV."""
        mock_df = pd.DataFrame(
            {
                "record_id": [12345],
                "mrn": [12345],
                "email_consent": ["alec@swamp.com"],
            }
        )
        mock_set_columns.return_value = mock_df
        mock_vars.redcap_import_file = temp_csv_file

        prepare_redcap_data(pd.DataFrame())
        assert temp_csv_file.exists()
        result = pd.read_csv(temp_csv_file)
        assert len(result) == 1

    @patch("hbnmigration.from_ripple.to_redcap.set_redcap_columns")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_csv_saved_without_index(self, mock_vars, mock_set_columns, temp_csv_file):
        """Test CSV is saved without index column."""
        mock_df = pd.DataFrame(
            {
                "record_id": [12345],
                "mrn": [12345],
                "email_consent": ["alec@swamp.com"],
            }
        )
        mock_set_columns.return_value = mock_df
        mock_vars.redcap_import_file = temp_csv_file

        prepare_redcap_data(pd.DataFrame())
        result = pd.read_csv(temp_csv_file)
        assert "Unnamed: 0" not in result.columns

    @patch("hbnmigration.from_ripple.to_redcap.set_redcap_columns")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_handles_large_dataset(self, mock_vars, mock_set_columns, temp_csv_file):
        """Test handling of larger datasets - Parliament of Trees assembly."""
        large_df = pd.DataFrame(
            {
                "record_id": range(10000, 10100),
                "mrn": range(10000, 10100),
                "email_consent": [f"member{i}@parliament.com" for i in range(100)],
            }
        )
        mock_set_columns.return_value = large_df
        mock_vars.redcap_import_file = temp_csv_file

        prepare_redcap_data(pd.DataFrame())
        result = pd.read_csv(temp_csv_file)
        assert len(result) == 100

    @patch("hbnmigration.from_ripple.to_redcap.set_redcap_columns")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_handles_special_characters_in_email(
        self, mock_vars, mock_set_columns, temp_csv_file
    ):
        """Test handling of special characters in email addresses."""
        mock_df = pd.DataFrame(
            {
                "record_id": [44001],
                "mrn": [44001],
                "email_consent": ["john.o'connor@parliament.org"],
                "firstName": ["John"],
            }
        )
        mock_set_columns.return_value = mock_df
        mock_vars.redcap_import_file = temp_csv_file

        prepare_redcap_data(pd.DataFrame())
        result = pd.read_csv(temp_csv_file)
        assert "john.o'connor@parliament.org" in result["email_consent"].values


class TestPushToRedcap:
    """Tests for push_to_redcap function."""

    @pytest.fixture
    def csv_with_content(self, temp_csv_file):
        """CSV file with test content."""
        temp_csv_file.write_text(
            "record_id,mrn,email_consent\n12345,12345,alec@swamp.com"
        )
        return temp_csv_file

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_successful_push(
        self, mock_vars, mock_post, csv_with_content, mock_redcap_response
    ):
        """Test successful push to REDCap."""
        mock_vars.redcap_import_file = csv_with_content
        mock_post.return_value = mock_redcap_response

        push_to_redcap("test_token_swamp_thing")
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["data"]["token"] == "test_token_swamp_thing"
        assert call_args[1]["data"]["content"] == "record"
        assert call_args[1]["data"]["action"] == "import"

    @pytest.mark.parametrize(
        "exception_class,error_message",
        [
            (requests.exceptions.Timeout, "Request timed out"),
            (requests.exceptions.ConnectionError, "Cannot connect"),
            (requests.exceptions.HTTPError, "500 Error"),
        ],
    )
    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_push_to_redcap_handles_errors(
        self, mock_vars, mock_post, csv_with_content, exception_class, error_message
    ):
        """Test push_to_redcap handles various exceptions."""
        mock_vars.redcap_import_file = csv_with_content
        mock_post.side_effect = exception_class(error_message)

        with pytest.raises(exception_class):
            push_to_redcap("test_token")

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_file_not_found_handles_gracefully(
        self, mock_vars, mock_post, temp_csv_file
    ):
        """Test handles missing file gracefully."""
        temp_csv_file.unlink(missing_ok=True)
        mock_vars.redcap_import_file = temp_csv_file

        push_to_redcap("test_token")
        mock_post.assert_not_called()


class TestSetStatusInRipple:
    """Tests for set_status_in_ripple function."""

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_successful_status_update(
        self,
        mock_vars,
        mock_endpoints,
        mock_post,
        excel_file_with_data,
        mock_ripple_response,
    ):
        """Test successful status update in Ripple."""
        mock_endpoints.Ripple.import_data.return_value = (
            "https://ripple.swamp.org/import"
        )
        mock_post.return_value = mock_ripple_response

        set_status_in_ripple("HBN - Main", str(excel_file_with_data))
        mock_post.assert_called_once()

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_empty_file_no_request(self, mock_vars, temp_excel_file):
        """Test empty Excel file doesn't trigger API request."""
        empty_df = pd.DataFrame()
        empty_df.to_excel(temp_excel_file, index=False)

        set_status_in_ripple("HBN - Main", str(temp_excel_file))

    def test_file_not_found_raises_exception(self, temp_excel_file):
        """Test FileNotFoundError is raised for missing file."""
        temp_excel_file.unlink(missing_ok=True)

        with pytest.raises(FileNotFoundError):
            set_status_in_ripple("HBN - Main", str(temp_excel_file))

    @pytest.mark.parametrize(
        "study_name",
        [
            "HBN - Main",
            "HBN - Waitlist",
        ],
    )
    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_different_studies(
        self,
        mock_vars,
        mock_endpoints,
        mock_post,
        excel_file_with_data,
        mock_ripple_response,
        study_name,
    ):
        """Test importing to different study types."""
        mock_endpoints.Ripple.import_data.return_value = (
            "https://ripple.swamp.org/import"
        )
        mock_post.return_value = mock_ripple_response

        set_status_in_ripple(study_name, str(excel_file_with_data))
        mock_post.assert_called_once()

    @pytest.mark.parametrize(
        "exception_class",
        [
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ],
    )
    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_handles_ripple_api_errors(
        self,
        mock_vars,
        mock_endpoints,
        mock_post,
        excel_file_with_data,
        exception_class,
    ):
        """Test handling of various Ripple API errors."""
        mock_endpoints.Ripple.import_data.return_value = (
            "https://ripple.swamp.org/import"
        )
        mock_post.side_effect = exception_class("API error")

        # The implementation wraps exceptions in RequestException
        with pytest.raises((exception_class, requests.exceptions.RequestException)):
            set_status_in_ripple("HBN - Main", str(excel_file_with_data))

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_large_excel_file_processing(
        self,
        mock_vars,
        mock_endpoints,
        mock_post,
        temp_excel_file,
        mock_ripple_response,
    ):
        """Test processing of large Excel file."""
        large_df = pd.DataFrame(
            {
                "globalId": [f"LRG{i:03d}" for i in range(1000)],
                "status": ["Sent to RedCap"] * 1000,
            }
        )
        large_df.to_excel(temp_excel_file, index=False)

        mock_endpoints.Ripple.import_data.return_value = (
            "https://ripple.swamp.org/import"
        )
        mock_post.return_value = mock_ripple_response

        set_status_in_ripple("HBN - Main", str(temp_excel_file))
        mock_post.assert_called_once()


class TestMain:
    """Tests for main function."""

    @pytest.mark.parametrize(
        "project_status,token_attr,token_value",
        [
            ("dev", "pid757", "dev_token_swamp"),
            ("prod", "pid247", "prod_token_parliament"),
        ],
    )
    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.set_status_in_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.push_to_redcap")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_redcap_data")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_workflow_by_project_status(
        self,
        mock_vars,
        mock_request,
        mock_prep_redcap,
        mock_prep_ripple,
        mock_push,
        mock_status,
        mock_cleanup,
        temp_excel_file,
        project_status,
        token_attr,
        token_value,
    ):
        """Test workflow for different project statuses."""
        setattr(mock_vars.Tokens, token_attr, token_value)

        mock_df = pd.DataFrame({"globalId": ["ST001"]})
        mock_request.return_value = mock_df
        mock_prep_ripple.return_value = {"HBN - Main": str(temp_excel_file)}

        main(project_status=project_status)

        mock_request.assert_called_once()
        mock_prep_redcap.assert_called_once()
        mock_prep_ripple.assert_called_once()
        mock_push.assert_called_once_with(token_value)
        mock_status.assert_called_once()
        assert_cleanup_called(mock_cleanup)

    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    def test_no_data_calls_cleanup(self, mock_request, mock_cleanup, mock_redcap_vars):
        """Test cleanup is called even when NoData is raised."""
        mock_redcap_vars.Tokens.pid757 = "dev_token"
        mock_request.side_effect = NoData

        main(project_status="dev")
        assert_cleanup_called(mock_cleanup)

    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.set_status_in_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.push_to_redcap")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_redcap_data")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_empty_ripple_prep_dict(
        self,
        mock_vars,
        mock_request,
        mock_prep_redcap,
        mock_prep_ripple,
        mock_push,
        mock_status,
        mock_cleanup,
    ):
        """Test when prepare_ripple_to_ripple returns empty dict."""
        mock_vars.Tokens.pid757 = "dev_token"
        mock_df = pd.DataFrame({"globalId": ["EMPT001"]})
        mock_request.return_value = mock_df
        mock_prep_ripple.return_value = {}

        main(project_status="dev")

        mock_push.assert_called_once()
        mock_status.assert_not_called()
        assert_cleanup_called(mock_cleanup)

    @pytest.mark.parametrize(
        "failing_function,exception_type",
        [
            ("mock_prep_redcap", ValueError),
            ("mock_prep_ripple", RuntimeError),
            ("mock_push", requests.exceptions.ConnectionError),
        ],
    )
    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.set_status_in_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.push_to_redcap")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_redcap_data")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_exception_triggers_cleanup(
        self,
        mock_vars,
        mock_request,
        mock_prep_redcap,
        mock_prep_ripple,
        mock_push,
        mock_status,
        mock_cleanup,
        failing_function,
        exception_type,
    ):
        """Test cleanup is called when any function in the workflow fails."""
        mock_vars.Tokens.pid757 = "dev_token"
        mock_df = pd.DataFrame({"globalId": ["ERR001"]})
        mock_request.return_value = mock_df
        mock_prep_ripple.return_value = {}

        failing_mock = locals()[failing_function]
        failing_mock.side_effect = exception_type("Operation failed")

        with pytest.raises(exception_type):
            main(project_status="dev")

        assert_cleanup_called(mock_cleanup)

    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.set_status_in_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.push_to_redcap")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_redcap_data")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_partial_ripple_update_failure(
        self,
        mock_vars,
        mock_request,
        mock_prep_redcap,
        mock_prep_ripple,
        mock_push,
        mock_status,
        mock_cleanup,
        temp_excel_file,
    ):
        """Test when one Ripple update succeeds but another fails."""
        mock_vars.Tokens.pid757 = "dev_token"

        mock_df = pd.DataFrame({"globalId": ["PRT001", "PRT002"]})
        mock_request.return_value = mock_df

        excel_file_2 = temp_excel_file.parent / "ripple_waitlist.xlsx"
        df2 = pd.DataFrame({"globalId": ["PRT002"]})
        df2.to_excel(excel_file_2, index=False)

        mock_prep_ripple.return_value = {
            "HBN - Main": str(temp_excel_file),
            "HBN - Waitlist": str(excel_file_2),
        }

        mock_status.side_effect = [
            None,
            requests.exceptions.RequestException("Second update failed"),
        ]

        with pytest.raises(requests.exceptions.RequestException):
            main(project_status="dev")

        assert_cleanup_called(mock_cleanup)

    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.set_status_in_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.push_to_redcap")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple")
    @patch("hbnmigration.from_ripple.to_redcap.prepare_redcap_data")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_multiple_studies_in_ripple_prep(
        self,
        mock_vars,
        mock_request,
        mock_prep_redcap,
        mock_prep_ripple,
        mock_push,
        mock_status,
        mock_cleanup,
        temp_excel_file,
    ):
        """Test workflow with multiple studies requiring Ripple updates."""
        mock_vars.Tokens.pid757 = "dev_token_parliament"

        mock_df = pd.DataFrame(
            {
                "globalId": ["WND001", "GRS001"],
                "firstName": ["Woodrue", "Constantine"],
            }
        )
        mock_request.return_value = mock_df

        excel_file_2 = temp_excel_file.parent / "ripple_waitlist.xlsx"
        df2 = pd.DataFrame({"globalId": ["GRS001"]})
        df2.to_excel(excel_file_2, index=False)

        mock_prep_ripple.return_value = {
            "HBN - Main": str(temp_excel_file),
            "HBN - Waitlist": str(excel_file_2),
        }

        main(project_status="dev")

        assert mock_status.call_count == 2
        assert_cleanup_called(mock_cleanup)


class TestIntegration:
    """Integration tests for the full workflow."""

    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_full_workflow_end_to_end(
        self,
        mock_rc_vars,
        mock_rp_vars,
        mock_endpoints,
        mock_post,
        mock_cleanup,
        temp_dir,
        mock_redcap_response,
    ):
        """Test complete end-to-end workflow with Swamp Thing data."""
        mock_rc_vars.Tokens.pid757 = "dev_token"
        mock_rc_vars.redcap_import_file = temp_dir / "redcap.csv"
        mock_rp_vars.ripple_import_file = temp_dir / "ripple.xlsx"
        mock_rp_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_rp_vars.column_dict.return_value = {}

        mock_endpoints.Ripple.import_data.return_value = "https://ripple.test/import"
        ripple_data = pd.DataFrame(
            {
                "globalId": ["ST001"],
                "customId": [12345],
                "firstName": ["Alec"],
                "cv.consent_form": ["Send to RedCap"],
                "contact.1.infos.1.contactType": ["email"],
                "contact.1.infos.1.information": ["alec@swamp.com"],
                "importType": ["HBN - Main"],
            }
        )
        mock_endpoints.Ripple.export_from_ripple.return_value = ripple_data
        mock_post.return_value = mock_redcap_response

        main(project_status="dev")
        assert mock_post.call_count >= 1
        assert_cleanup_called(mock_cleanup)
