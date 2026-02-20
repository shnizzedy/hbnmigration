"""Tests for Ripple sourced data migration."""

from unittest.mock import patch

import pandas as pd
import pytest
import requests

from hbnmigration.exceptions import NoData
from hbnmigration.from_ripple.to_redcap import (
    Endpoints,
    main,
    prepare_redcap_data,
    push_to_redcap,
    request_potential_participants,
    set_redcap_columns,
    set_status_in_ripple,
)


class TestEndpoints:
    """Tests for Endpoints dataclass."""

    def test_endpoints_initialization(self):
        """Test that Endpoints properly initializes REDCap and Ripple endpoints."""
        endpoints = Endpoints()
        assert hasattr(endpoints, "REDCap")
        assert hasattr(endpoints, "Ripple")

    def test_endpoints_are_accessible(self):
        """Test that endpoint attributes can be accessed."""
        endpoints = Endpoints()
        assert endpoints.REDCap is not None
        assert endpoints.Ripple is not None


class TestRequestPotentialParticipants:
    """Tests for request_potential_participants function."""

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_successful_request_with_valid_data(self, mock_vars, sample_ripple_data):
        """Test successful API request returns filtered DataFrame."""
        mock_vars.export_from_ripple.return_value = sample_ripple_data
        mock_vars.study_ids = {
            "HBN - Main": "main_study_id",
            "HBN - Waitlist": "waitlist_study_id",
        }
        mock_vars.column_dict.return_value = {}

        result = request_potential_participants()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 4
        assert all(result["cv.consent_form"] == "Send to RedCap")

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_empty_dataframe_raises_no_data(self, mock_vars):
        """Test empty DataFrame raises NoData exception."""
        mock_vars.export_from_ripple.return_value = pd.DataFrame()
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}

        with pytest.raises(NoData):
            request_potential_participants()

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_no_send_to_redcap_raises_no_data(
        self, mock_vars, anton_arcane_corrupted_data
    ):
        """Test no 'Send to RedCap' records raises NoData."""
        mock_vars.export_from_ripple.return_value = anton_arcane_corrupted_data
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}

        with pytest.raises(NoData):
            request_potential_participants()

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_filters_consent_form_correctly(self, mock_vars):
        """Test filtering by consent form status."""
        mock_df = pd.DataFrame(
            {
                "globalId": ["ST001", "AA001", "ANT001"],
                "firstName": ["Alec", "Abby", "Anton"],
                "cv.consent_form": ["Send to RedCap", "Send to RedCap", "Pending"],
                "customId": [1, 2, 3],
            }
        )
        mock_vars.export_from_ripple.return_value = mock_df
        mock_vars.study_ids = {"HBN - Main": "main_study_id"}
        mock_vars.column_dict.return_value = {}

        result = request_potential_participants()

        assert len(result) == 2
        assert "ANT001" not in result["globalId"].values

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_multiple_studies_concatenation(self, mock_vars):
        """Test data from multiple studies is properly concatenated."""
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

        mock_vars.export_from_ripple.side_effect = [mock_df_main, mock_df_waitlist]
        mock_vars.study_ids = {
            "HBN - Main": "main_study_id",
            "HBN - Waitlist": "waitlist_study_id",
        }
        mock_vars.column_dict.return_value = {}

        result = request_potential_participants()

        assert len(result) == 2
        assert set(result["globalId"].values) == {"ST001", "AA001"}


class TestSetRedcapColumns:
    """Tests for set_redcap_columns function."""

    def test_basic_column_renaming(self):
        """Test basic column renaming and selection."""
        ripple_df = pd.DataFrame(
            {
                "customId": [12345],
                "globalId": ["ST001"],
                "firstName": ["Alec"],
                "contact.1.infos.1.contactType": ["email"],
                "contact.1.infos.1.information": ["alec.holland@swampthing.com"],
            }
        )

        result = set_redcap_columns(ripple_df)

        assert "record_id" in result.columns
        assert "mrn" in result.columns
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

        assert "email_consent" in result.columns
        assert result["email_consent"].iloc[0] == "abby.arcane@parliament.org"

    # ... other tests remain the same ...


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

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    def test_csv_content_in_request(
        self, mock_vars, mock_post, csv_with_content, mock_redcap_response
    ):
        """Test CSV content is properly included in request."""
        mock_vars.redcap_import_file = csv_with_content
        mock_post.return_value = mock_redcap_response

        push_to_redcap("test_token")

        call_args = mock_post.call_args
        assert "alec@swamp.com" in call_args[1]["data"]["data"]

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
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    def test_successful_status_update(
        self, mock_ep, mock_vars, mock_post, excel_file_with_data, mock_ripple_response
    ):
        """Test successful status update in Ripple."""
        mock_ep.Ripple.import_data.return_value = "https://ripple.swamp.org/import"
        mock_vars.headers = {"import": {"Content-Type": "application/octet-stream"}}
        mock_post.return_value = mock_ripple_response

        set_status_in_ripple("HBN - Main", str(excel_file_with_data))

        mock_post.assert_called_once()

    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    def test_empty_file_no_request(self, mock_vars, temp_excel_file):
        """Test empty Excel file doesn't trigger API request."""
        empty_df = pd.DataFrame()
        empty_df.to_excel(temp_excel_file, index=False)
        mock_vars.headers = {"import": {}}

        set_status_in_ripple("HBN - Main", str(temp_excel_file))

    def test_file_not_found_raises_exception(self, temp_excel_file):
        """Test FileNotFoundError is raised for missing file."""
        temp_excel_file.unlink(missing_ok=True)

        with pytest.raises(FileNotFoundError):
            set_status_in_ripple("HBN - Main", str(temp_excel_file))

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    def test_request_exception_is_raised(
        self, mock_ep, mock_vars, mock_post, excel_file_with_data
    ):
        """Test RequestException is properly raised and re-raised."""
        mock_ep.Ripple.import_data.return_value = "https://ripple.swamp.org/import"
        mock_vars.headers = {"import": {}}
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        with pytest.raises(requests.exceptions.RequestException):
            set_status_in_ripple("HBN - Main", str(excel_file_with_data))

    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    def test_uses_correct_headers(
        self, mock_ep, mock_vars, mock_post, excel_file_with_data, mock_ripple_response
    ):
        """Test correct headers are used in request."""
        mock_ep.Ripple.import_data.return_value = "https://ripple.swamp.org/import"
        mock_vars.headers = {
            "import": {
                "Content-Type": "application/octet-stream",
                "X-Swamp-Token": "green",
            }
        }
        mock_post.return_value = mock_ripple_response

        set_status_in_ripple("HBN - Main", str(excel_file_with_data))

        call_args = mock_post.call_args
        assert call_args[1]["headers"] == mock_vars.headers["import"]


class TestMain:
    """Tests for main function."""

    @pytest.fixture
    def mock_all_main_deps(self):
        """Mock all main function dependencies."""
        with (
            patch("hbnmigration.from_ripple.to_redcap.cleanup") as mock_cleanup,
            patch(
                "hbnmigration.from_ripple.to_redcap.set_status_in_ripple"
            ) as mock_status,
            patch("hbnmigration.from_ripple.to_redcap.push_to_redcap") as mock_push,
            patch(
                "hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple"
            ) as mock_prep_ripple,
            patch(
                "hbnmigration.from_ripple.to_redcap.prepare_redcap_data"
            ) as mock_prep_redcap,
            patch(
                "hbnmigration.from_ripple.to_redcap.request_potential_participants"
            ) as mock_request,
            patch("hbnmigration.from_ripple.to_redcap.redcap_variables") as mock_vars,
        ):
            yield {
                "cleanup": mock_cleanup,
                "set_status": mock_status,
                "push": mock_push,
                "prep_ripple": mock_prep_ripple,
                "prep_redcap": mock_prep_redcap,
                "request": mock_request,
                "vars": mock_vars,
            }

    def test_successful_dev_workflow(self, mock_all_main_deps, temp_excel_file):
        """Test successful development workflow."""
        mocks = mock_all_main_deps
        mocks["vars"].Tokens.pid757 = "dev_token_swamp"
        mock_df = pd.DataFrame({"globalId": ["ST001"]})
        mocks["request"].return_value = mock_df
        mocks["prep_ripple"].return_value = {"HBN - Main": str(temp_excel_file)}

        main(project_status="dev")

        mocks["request"].assert_called_once()
        mocks["prep_redcap"].assert_called_once()
        mocks["prep_ripple"].assert_called_once()
        mocks["push"].assert_called_once_with("dev_token_swamp")
        mocks["set_status"].assert_called_once()
        mocks["cleanup"].assert_called_once()

    def test_successful_prod_workflow(self, mock_all_main_deps, temp_excel_file):
        """Test successful production workflow."""
        mocks = mock_all_main_deps
        mocks["vars"].Tokens.pid247 = "prod_token_parliament"
        mock_df = pd.DataFrame({"globalId": ["ST001"]})
        mocks["request"].return_value = mock_df
        mocks["prep_ripple"].return_value = {"HBN - Main": str(temp_excel_file)}

        main(project_status="prod")

        mocks["push"].assert_called_once_with("prod_token_parliament")

    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.request_potential_participants")
    def test_no_data_calls_cleanup(self, mock_request, mock_cleanup):
        """Test cleanup is called even when NoData is raised."""
        mock_request.side_effect = NoData

        main(project_status="dev")

        mock_cleanup.assert_called_once()


class TestIntegration:
    """Integration tests for the full workflow."""

    @patch("hbnmigration.from_ripple.to_redcap.cleanup")
    @patch("hbnmigration.from_ripple.to_redcap.requests.post")
    @patch("hbnmigration.from_ripple.to_redcap.ripple_variables")
    @patch("hbnmigration.from_ripple.to_redcap.redcap_variables")
    @patch("hbnmigration.from_ripple.to_redcap.Endpoints")
    def test_full_workflow_end_to_end(
        self,
        mock_ep,
        mock_rc_vars,
        mock_rp_vars,
        mock_post,
        mock_cleanup,
        temp_dir,
        mock_redcap_response,
    ):
        """Test complete end-to-end workflow."""
        mock_rc_vars.Tokens.pid757 = "dev_token"
        mock_rc_vars.redcap_import_file = temp_dir / "redcap.csv"
        mock_rp_vars.ripple_import_file = temp_dir / "ripple.xlsx"
        mock_rp_vars.headers = {"import": {}}
        mock_rp_vars.study_ids = {"HBN - Main": "study123"}
        mock_rp_vars.column_dict.return_value = {}
        mock_ep.Ripple.import_data.return_value = "https://ripple.test/import"

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
        mock_rp_vars.export_from_ripple.return_value = ripple_data
        mock_post.return_value = mock_redcap_response

        main(project_status="dev")

        assert mock_post.call_count >= 1
        mock_cleanup.assert_called_once()
