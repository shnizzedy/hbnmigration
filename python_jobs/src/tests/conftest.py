"""Shared pytest configuration and fixtures."""

from contextlib import ExitStack
from pathlib import Path
import tempfile
from unittest.mock import Mock, patch

import pandas as pd
import pytest

# ============================================================================
# File System Fixtures
# ============================================================================


@pytest.fixture
def temp_csv_file():
    """Create a temporary CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
        tmp_path = tmp.name
    yield Path(tmp_path)
    Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_excel_file():
    """Create a temporary Excel file."""
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp_path = tmp.name
    yield Path(tmp_path)
    Path(tmp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# API Response Fixtures
# ============================================================================


@pytest.fixture
def mock_redcap_response():
    """Mock successful REDCap API response."""
    response = Mock()
    response.status_code = 200
    response.text = "1"
    return response


@pytest.fixture
def mock_ripple_response():
    """Mock successful Ripple API response."""
    response = Mock()
    response.status_code = 200
    response.text = "Success"
    return response


# ============================================================================
# Participant Data Fixtures - Swamp Thing Universe
# ============================================================================


@pytest.fixture
def participant_with_email():
    """Return generic participant with email contact."""
    return pd.DataFrame(
        {
            "customId": [12345],
            "globalId": ["TEST001"],
            "firstName": ["Test"],
            "contact.1.infos.1.contactType": ["email"],
            "contact.1.infos.1.information": ["test@swamp.com"],
        }
    )


@pytest.fixture
def participant_without_email():
    """Return generic participant without email contact."""
    return pd.DataFrame(
        {
            "customId": [67890],
            "globalId": ["TEST002"],
            "firstName": ["NoEmail"],
            "contact.1.infos.1.contactType": ["phone"],
            "contact.1.infos.1.information": ["555-0123"],
        }
    )


@pytest.fixture
def send_to_redcap_participant():
    """Participant with 'Send to RedCap' consent status."""
    return pd.DataFrame(
        {
            "globalId": ["TEST003"],
            "firstName": ["Ready"],
            "cv.consent_form": ["Send to RedCap"],
            "customId": [99999],
        }
    )


@pytest.fixture
def sample_ripple_data():
    """Sample Ripple data with multiple participants - Alec Holland & Abby Arcane."""
    return pd.DataFrame(
        {
            "globalId": ["ST001", "AA001", "TE001", "WOO001"],
            "firstName": ["Alec", "Abby", "Tefé", "Woodrue"],
            "lastName": ["Holland", "Arcane", "Holland", "Jason"],
            "cv.consent_form": [
                "Send to RedCap",
                "Send to RedCap",
                "Send to RedCap",
                "Send to RedCap",
            ],
            "customId": [12345, 67890, 11111, 22222],
            "contact.1.infos.1.contactType": ["email", "email", "email", "email"],
            "contact.1.infos.1.information": [
                "alec@swamp.com",
                "abby@parliament.org",
                "tefe@green.org",
                "woodrue@floronic.com",
            ],
            "importType": [
                "HBN - Main",
                "HBN - Waitlist",
                "HBN - Main",
                "HBN - Waitlist",
            ],
        }
    )


@pytest.fixture
def swamp_thing_participant():
    """Fixture providing Alec Holland's data."""
    return pd.DataFrame(
        {
            "globalId": ["ST001"],
            "customId": [12345],
            "firstName": ["Alec"],
            "lastName": ["Holland"],
            "cv.consent_form": ["Send to RedCap"],
            "contact.1.infos.1.contactType": ["email"],
            "contact.1.infos.1.information": ["alec.holland@swampthing.com"],
            "importType": ["HBN - Main"],
        }
    )


@pytest.fixture
def parliament_of_trees_participants():
    """Fixture providing multiple Parliament of Trees members."""
    return pd.DataFrame(
        {
            "globalId": ["ST001", "AA001", "TE001"],
            "customId": [12345, 67890, 11111],
            "firstName": ["Alec", "Abby", "Tefé"],
            "lastName": ["Holland", "Arcane", "Holland"],
            "cv.consent_form": ["Send to RedCap", "Send to RedCap", "Send to RedCap"],
            "contact.1.infos.1.contactType": ["email", "email", "email"],
            "contact.1.infos.1.information": [
                "alec@swamp.com",
                "abby@parliament.org",
                "tefe@green.org",
            ],
            "importType": ["HBN - Main", "HBN - Main", "HBN - Waitlist"],
        }
    )


@pytest.fixture
def anton_arcane_corrupted_data():
    """Fixture providing Anton Arcane's corrupted/rejected participant data."""
    return pd.DataFrame(
        {
            "globalId": ["ANT001"],
            "customId": [66666],
            "firstName": ["Anton"],
            "lastName": ["Arcane"],
            "cv.consent_form": ["Do Not Send"],
            "contact.1.infos.1.contactType": ["phone"],
            "contact.1.infos.1.information": ["666-666-6666"],
            "importType": ["HBN - Rejected"],
        }
    )


# ============================================================================
# Mock Configuration Fixtures
# ============================================================================


@pytest.fixture
def mock_ripple_variables():
    """Mock ripple_variables configuration with common defaults."""
    mock_vars = Mock()
    mock_vars.study_ids = {
        "HBN - Main": "main_study_id",
        "HBN - Waitlist": "waitlist_study_id",
    }
    mock_vars.column_dict.return_value = {}
    mock_vars.headers = {"import": {"Content-Type": "application/octet-stream"}}
    return mock_vars


@pytest.fixture
def mock_redcap_variables():
    """Mock redcap_variables configuration."""
    mock_vars = Mock()
    mock_vars.Tokens.pid757 = "dev_token"
    mock_vars.Tokens.pid247 = "prod_token"
    return mock_vars


@pytest.fixture
def setup_redcap_mocks(mock_redcap_variables, temp_csv_file):
    """Set up common redcap variable mocks with temp file."""
    mock_redcap_variables.redcap_import_file = temp_csv_file
    return mock_redcap_variables


@pytest.fixture
def excel_file_with_data(temp_excel_file):
    """Create Excel file with test data - Swamp Thing consent completed."""
    test_df = pd.DataFrame(
        {
            "globalId": ["ST001"],
            "cv.consent_form": ["consent_form_created_in_redcap"],
        }
    )
    test_df.to_excel(temp_excel_file, index=False)
    return temp_excel_file


# ============================================================================
# Complex Mock Fixtures
# ============================================================================


@pytest.fixture
def mock_all_ripple_deps(mock_ripple_variables):
    """Set up all common Ripple dependencies with Endpoints."""
    mock_endpoints = Mock()
    return {
        "endpoints": mock_endpoints,
        "variables": mock_ripple_variables,
    }


@pytest.fixture
def mock_endpoints():
    """Mock Endpoints configuration."""
    mock = Mock()
    mock.Ripple.import_data.return_value = "https://ripple.swamp.org/import"
    mock.Ripple.export_from_ripple.return_value = pd.DataFrame()
    mock.REDCap.base_url = "https://redcap.swamp.org/api/"
    return mock


@pytest.fixture
def mock_main_workflow_deps(mock_redcap_variables, temp_excel_file):
    """Set up dependencies for main workflow tests."""
    return {
        "vars": mock_redcap_variables,
        "excel_file": temp_excel_file,
    }


@pytest.fixture
def patched_main_workflow():
    """Context manager for patching main workflow dependencies."""
    patches = {
        "cleanup": "hbnmigration.from_ripple.to_redcap.cleanup",
        "set_status": "hbnmigration.from_ripple.to_redcap.set_status_in_ripple",
        "push": "hbnmigration.from_ripple.to_redcap.push_to_redcap",
        "prep_ripple": "hbnmigration.from_ripple.to_redcap.prepare_ripple_to_ripple",
        "prep_redcap": "hbnmigration.from_ripple.to_redcap.prepare_redcap_data",
        "request": "hbnmigration.from_ripple.to_redcap.request_potential_participants",
        "vars": "hbnmigration.from_ripple.to_redcap.redcap_variables",
    }

    with ExitStack() as stack:
        mocks = {
            name: stack.enter_context(patch(path)) for name, path in patches.items()
        }
        yield mocks


# ============================================================================
# Helper Functions
# ============================================================================


def assert_valid_redcap_columns(result_df):
    """Assert DataFrame has valid REDCap columns."""
    assert "record_id" in result_df.columns
    assert "mrn" in result_df.columns
    assert result_df["record_id"].iloc[0] is not None


def assert_valid_email_extraction(result_df, expected_email):
    """Assert email was properly extracted."""
    assert "email_consent" in result_df.columns
    assert result_df["email_consent"].iloc[0] == expected_email


def assert_cleanup_called(mock_cleanup):
    """Assert cleanup was called exactly once."""
    mock_cleanup.assert_called_once()


def create_participant_df(**kwargs):
    """
    Create participant DataFrames with defaults.

    Args:
        **kwargs: Override default values

    Returns:
        pd.DataFrame: Participant data

    """
    defaults = {
        "globalId": ["CUSTOM001"],
        "customId": [99999],
        "firstName": ["Custom"],
        "lastName": ["Participant"],
        "cv.consent_form": ["Send to RedCap"],
        "contact.1.infos.1.contactType": ["email"],
        "contact.1.infos.1.information": ["custom@test.com"],
        "importType": ["HBN - Main"],
    }
    defaults.update(kwargs)
    return pd.DataFrame(defaults)
