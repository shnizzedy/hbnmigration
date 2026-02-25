"""Shared pytest configuration and fixtures."""

from contextlib import contextmanager, ExitStack
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional, TypedDict
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


def _create_mock_response(status_code: int, text: str) -> Mock:
    """Create mock API responses."""
    response = Mock()
    response.status_code = status_code
    response.text = text
    return response


@pytest.fixture
def mock_redcap_response():
    """Mock successful REDCap API response."""
    return _create_mock_response(200, "1")


@pytest.fixture
def mock_ripple_response():
    """Mock successful Ripple API response."""
    return _create_mock_response(200, "Success")


# ============================================================================
# Participant Data Fixtures - Base Factory
# ============================================================================


def create_participant_df(  # noqa: PLR0913
    global_ids: Optional[List[str]] = None,
    custom_ids: Optional[List[int]] = None,
    first_names: Optional[List[str]] = None,
    last_names: Optional[List[str]] = None,
    consent_forms: Optional[List[str]] = None,
    contact_types: Optional[List[str]] = None,
    contact_info: Optional[List[str]] = None,
    import_types: Optional[List[str]] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    Create participant DataFrames with flexible defaults.

    Args:
        global_ids: List of global IDs
        custom_ids: List of custom IDs
        first_names: List of first names
        last_names: List of last names
        consent_forms: List of consent form statuses
        contact_types: List of contact types
        contact_info: List of contact information
        import_types: List of import types
        **kwargs: Additional columns to add

    Returns:
        pd.DataFrame: Participant data

    """
    # Determine length from first provided list or default to 1
    length = len(global_ids or custom_ids or first_names or [1])

    data = {
        "globalId": global_ids or [f"CUSTOM{i:03d}" for i in range(1, length + 1)],
        "customId": custom_ids or list(range(99999, 99999 + length)),
        "firstName": first_names or ["Custom"] * length,
        "lastName": last_names or ["Participant"] * length,
        "cv.consent_form": consent_forms or ["Send to RedCap"] * length,
        "contact.1.infos.1.contactType": contact_types or ["email"] * length,
        "contact.1.infos.1.information": contact_info
        or [f"custom{i}@test.com" for i in range(1, length + 1)],
        "importType": import_types or ["HBN - Main"] * length,
    }

    # Add any additional columns
    data.update(kwargs)

    return pd.DataFrame(data)


# ============================================================================
# Participant Data Fixtures
# ============================================================================


@pytest.fixture
def participant_with_email():
    """Return generic participant with email contact."""
    return create_participant_df(
        global_ids=["TEST001"],
        custom_ids=[12345],
        first_names=["Test"],
        contact_types=["email"],
        contact_info=["test@swamp.com"],
    )


@pytest.fixture
def participant_without_email():
    """Return generic participant without email contact."""
    return create_participant_df(
        global_ids=["TEST002"],
        custom_ids=[67890],
        first_names=["NoEmail"],
        contact_types=["phone"],
        contact_info=["555-0123"],
    )


@pytest.fixture
def send_to_redcap_participant():
    """Participant with 'Send to RedCap' consent status."""
    return create_participant_df(
        global_ids=["TEST003"],
        custom_ids=[99999],
        first_names=["Ready"],
        consent_forms=["Send to RedCap"],
    )


@pytest.fixture
def swamp_thing_participant():
    """Fixture providing Alec Holland's data."""
    return create_participant_df(
        global_ids=["ST001"],
        custom_ids=[12345],
        first_names=["Alec"],
        last_names=["Holland"],
        contact_info=["alec.holland@swampthing.com"],
        import_types=["HBN - Main"],
    )


@pytest.fixture
def parliament_of_trees_participants():
    """Fixture providing multiple Parliament of Trees members."""
    return create_participant_df(
        global_ids=["ST001", "AA001", "TE001"],
        custom_ids=[12345, 67890, 11111],
        first_names=["Alec", "Abby", "Tefé"],
        last_names=["Holland", "Arcane", "Holland"],
        contact_info=["alec@swamp.com", "abby@parliament.org", "tefe@green.org"],
        import_types=["HBN - Main", "HBN - Main", "HBN - Waitlist"],
    )


@pytest.fixture
def sample_ripple_data():
    """Sample Ripple data with multiple participants - Alec Holland & Abby Arcane."""
    return create_participant_df(
        global_ids=["ST001", "AA001", "TE001", "WOO001"],
        custom_ids=[12345, 67890, 11111, 22222],
        first_names=["Alec", "Abby", "Tefé", "Woodrue"],
        last_names=["Holland", "Arcane", "Holland", "Jason"],
        contact_info=[
            "alec@swamp.com",
            "abby@parliament.org",
            "tefe@green.org",
            "woodrue@floronic.com",
        ],
        import_types=["HBN - Main", "HBN - Waitlist", "HBN - Main", "HBN - Waitlist"],
    )


@pytest.fixture
def anton_arcane_corrupted_data():
    """Fixture providing Anton Arcane's corrupted/rejected participant data."""
    return create_participant_df(
        global_ids=["ANT001"],
        custom_ids=[66666],
        first_names=["Anton"],
        last_names=["Arcane"],
        consent_forms=["Do Not Send"],
        contact_types=["phone"],
        contact_info=["666-666-6666"],
        import_types=["HBN - Rejected"],
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
def mock_endpoints():
    """Mock Endpoints configuration."""
    mock = Mock()
    mock.Ripple.import_data.return_value = "https://ripple.swamp.org/import"
    mock.Ripple.export_from_ripple.return_value = pd.DataFrame()
    mock.REDCap.base_url = "https://redcap.swamp.org/api/"
    return mock


@pytest.fixture
def mock_all_ripple_deps(mock_ripple_variables, mock_endpoints):
    """Set up all common Ripple dependencies with Endpoints."""
    return {
        "endpoints": mock_endpoints,
        "variables": mock_ripple_variables,
    }


@pytest.fixture
def mock_main_workflow_deps(mock_redcap_variables, temp_excel_file):
    """Set up dependencies for main workflow tests."""
    return {
        "vars": mock_redcap_variables,
        "excel_file": temp_excel_file,
    }


# ============================================================================
# Excel File Fixtures
# ============================================================================


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
# Import Testing Fixtures
# ============================================================================


@pytest.fixture
def mock_importable_module():
    """Create a mock module with test attributes."""
    mock_mod = Mock()
    mock_mod.TestClass = Mock
    mock_mod.TestClass.__name__ = "TestClass"
    mock_mod.test_function = lambda x: x * 2
    mock_mod.TEST_CONSTANT = "test_value"
    return mock_mod


class FallbackDataDict(TypedDict):
    """Typing for fallback data dict."""

    parliament: dict[str, list[str]]
    avatars: list[str]
    members: list[str]


@pytest.fixture
def swamp_thing_fallback_data() -> FallbackDataDict:
    """Complex fallback data structure for testing - Parliament of Trees structure."""
    return {
        "parliament": {
            "trees": ["Yggdrasil", "Ghost Orchid"],
            "stones": ["Parliament of Stones"],
            "waves": ["Parliament of Waves"],
        },
        "avatars": ["Swamp Thing", "Black Orchid", "Poison Ivy"],
        "members": ["Alec Holland", "Abby Arcane", "Tefé Holland"],
    }


@pytest.fixture
def green_realm_config():
    """Mock configuration data for API testing."""
    return {
        "api_key": "TEST_KEY",
        "endpoint": "https://green.realm/api",
        "timeout": 30,
        "retry_attempts": 3,
    }


@pytest.fixture
def mock_parliament_object():
    """Mock Parliament of Trees object for testing."""
    mock_parliament = Mock()
    mock_parliament.members = ["Alec Holland", "Ghost Orchid", "Yggdrasil"]
    mock_parliament.collective_consciousness = True
    mock_parliament.green_connection = Mock()
    return mock_parliament


# ============================================================================
# Workflow Patching Fixtures
# ============================================================================


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
# Helper Functions - Assertions
# ============================================================================


def assert_valid_redcap_columns(result_df: pd.DataFrame) -> None:
    """Assert DataFrame has valid REDCap columns."""
    assert "record_id" in result_df.columns
    assert "mrn" in result_df.columns
    assert result_df["record_id"].iloc[0] is not None


def assert_valid_email_extraction(result_df: pd.DataFrame, expected_email: str) -> None:
    """Assert email was properly extracted."""
    assert "email_consent" in result_df.columns
    assert result_df["email_consent"].iloc[0] == expected_email


def assert_cleanup_called(mock_cleanup: Mock) -> None:
    """Assert cleanup was called exactly once."""
    mock_cleanup.assert_called_once()


def assert_is_fallback_value(result: Any, expected_fallback: Any) -> None:
    """Assert that result matches the expected fallback value."""
    assert result == expected_fallback


def assert_not_fallback_value(result: Any, fallback: Any) -> None:
    """Assert that result is NOT the fallback (successful import)."""
    assert result != fallback


def assert_is_callable_result(result: Any) -> None:
    """Assert result is callable (function/method)."""
    assert callable(result)


def assert_has_name_attribute(result: Any, expected_name: str) -> None:
    """Assert result has __name__ attribute with expected value."""
    assert hasattr(result, "__name__")
    assert result.__name__ == expected_name


# ============================================================================
# Helper Functions - Module Mocking
# ============================================================================


@contextmanager
def create_mock_module_in_sys(
    module_path: str, attributes: Optional[Dict[str, Any]] = None
):
    """
    Context manager to temporarily add mock module to sys.modules.

    Args:
        module_path: String path like 'parent.child.module'
        attributes: Dict of attributes to add to module

    Usage:
        with create_mock_module_in_sys('test.module', {'attr': 'value'}):
            # test code here

    """
    mock_mod = Mock()
    if attributes:
        for key, value in attributes.items():
            setattr(mock_mod, key, value)

    with patch.dict("sys.modules", {module_path: mock_mod}):
        yield mock_mod
