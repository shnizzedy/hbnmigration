"""Shared pytest configuration and fixtures."""

from pathlib import Path
import tempfile
from unittest.mock import Mock

import pandas as pd
import pytest


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


@pytest.fixture
def sample_ripple_data():
    """Sample Ripple data for testing."""
    return pd.DataFrame(
        {
            "globalId": ["ST001", "AA001"],
            "firstName": ["Alec", "Abby"],
            "lastName": ["Holland", "Arcane"],
            "cv.consent_form": ["Send to RedCap", "Send to RedCap"],
            "customId": [12345, 67890],
            "contact.1.infos.1.contactType": ["email", "email"],
            "contact.1.infos.1.information": ["alec@swamp.com", "abby@parliament.org"],
            "importType": ["HBN - Main", "HBN - Waitlist"],
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
    """Fixture providing Anton Arcane's corrupted participant data."""
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


@pytest.fixture
def mock_ripple_variables():
    """Mock ripple_variables configuration."""
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
def mock_endpoints():
    """Mock Endpoints configuration."""
    mock = Mock()
    mock.Ripple.import_data.return_value = "https://ripple.swamp.org/import"
    mock.REDCap.base_url = "https://redcap.swamp.org/api/"
    return mock


@pytest.fixture
def setup_ripple_mocks(mock_ripple_variables):
    """Set up common ripple variable mocks."""
    return mock_ripple_variables


@pytest.fixture
def setup_redcap_mocks(mock_redcap_variables, temp_csv_file):
    """Set up common redcap variable mocks with temp file."""
    mock_redcap_variables.redcap_import_file = temp_csv_file
    return mock_redcap_variables


@pytest.fixture
def excel_file_with_data(temp_excel_file):
    """Create Excel file with test data."""
    test_df = pd.DataFrame(
        {
            "globalId": ["ST001"],
            "cv.consent_form": ["consent_form_created_in_redcap"],
        }
    )
    test_df.to_excel(temp_excel_file, index=False)
    return temp_excel_file
