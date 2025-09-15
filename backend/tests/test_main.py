import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import app
from services import transcripts


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_mint_access_token():
    with patch('main.mint_access_token') as mock:
        mock.return_value = "mock_token"
        yield mock


@pytest.fixture
def mock_generate_summary():
    with patch('main.generate_summary') as mock:
        mock.return_value = "Mock summary of the conversation."
        yield mock


@pytest.fixture
def mock_validate_room_membership():
    with patch('main.validate_room_membership') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_twilio_client():
    with patch('twilio.rest.Client') as mock:
        mock_instance = MagicMock()
        mock_call = MagicMock()
        mock_call.sid = "mock_call_sid"
        mock_call.status = "in-progress"
        mock_instance.calls.create.return_value = mock_call
        mock.return_value = mock_instance
        yield mock


def test_create_room(client, mock_mint_access_token):
    """Test that the create-room endpoint returns a 200 status code and a token."""
    response = client.post(
        "/create-room",
        json={"identity": "test-user", "role": "agent"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "room_name" in data
    assert data["token"] == "mock_token"
    mock_mint_access_token.assert_called_once()


def test_join_token(client, mock_mint_access_token):
    """Test that the join-token endpoint returns a 200 status code and a token."""
    response = client.post(
        "/join-token",
        json={"room_name": "test-room", "identity": "test-user"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "mock_token"
    mock_mint_access_token.assert_called_once()


def test_transfer(client, mock_mint_access_token, mock_generate_summary):
    """Test that the transfer endpoint returns a 200 status code and the expected response."""
    # Set up API key for protected endpoint
    os.environ["ADMIN_API_KEY"] = "test-key"
    
    response = client.post(
        "/transfer",
        json={
            "from_room": "test-room-1",
            "initiator_identity": "agent-a",
            "target_identity": "agent-b",
            "transcript": "This is a test transcript."
        },
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "to_room" in data
    assert data["initiator_token"] == "mock_token"
    assert data["target_token"] == "mock_token"
    assert data["caller_token"] == "mock_token"
    assert data["summary"] == "Mock summary of the conversation."
    assert mock_mint_access_token.call_count == 3
    mock_generate_summary.assert_called_once()


def test_room_summary(client):
    """Test that the room summary endpoint returns a 200 status code and the expected response."""
    # Set up a room with a summary and transcript
    room_name = "test-room-summary"
    summary_text = "Test summary"
    transcript_text = "Test transcript"
    transcripts.set_room_summary(room_name, summary_text)
    transcripts.set_room_transcript(room_name, transcript_text)
    
    response = client.get(f"/room/{room_name}/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == summary_text
    assert data["transcript"] == transcript_text


def test_validate_membership(client, mock_validate_room_membership):
    """Test that the validate-membership endpoint returns a 200 status code and the expected response."""
    # Set up API key for protected endpoint
    os.environ["ADMIN_API_KEY"] = "test-key"
    
    response = client.post(
        "/validate-membership",
        json={
            "room_name": "test-room",
            "identity": "test-user"
        },
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_member"] is True
    assert "test-user" in data["message"]
    mock_validate_room_membership.assert_called_once()


def test_twilio_transfer(client, mock_twilio_client, mock_generate_summary):
    """Test that the twilio-transfer endpoint returns a 200 status code and the expected response."""
    # Set up API key for protected endpoint
    os.environ["ADMIN_API_KEY"] = "test-key"
    # Set up Twilio environment variables
    os.environ["TWILIO_ACCOUNT_SID"] = "test-sid"
    os.environ["TWILIO_AUTH_TOKEN"] = "test-token"
    os.environ["TWILIO_PHONE_NUMBER"] = "+12345678901"
    
    response = client.post(
        "/twilio-transfer",
        json={
            "from_room": "test-room",
            "phone_number": "+12345678901"
        },
        headers={"X-API-Key": "test-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["call_sid"] == "mock_call_sid"
    assert data["to_number"] == "+12345678901"
    assert data["status"] == "in-progress"
    mock_twilio_client.assert_called_once()
    mock_generate_summary.assert_called_once()


def test_twilio_call_status(client, mock_twilio_client):
    """Test that the twilio-call-status endpoint returns a 200 status code and the expected response."""
    # Set up a room with call status
    room_name = "test-room-call"
    from services.database import set_call_status
    set_call_status(
        room_name=room_name,
        twilio_call_sid="mock_call_sid",
        status="in-progress",
        phone_number="+12345678901"
    )
    
    # Set up Twilio environment variables
    os.environ["TWILIO_ACCOUNT_SID"] = "test-sid"
    os.environ["TWILIO_AUTH_TOKEN"] = "test-token"
    
    # Mock the Twilio client calls method
    mock_instance = mock_twilio_client.return_value
    mock_calls = MagicMock()
    mock_call = MagicMock()
    mock_call.status = "completed"
    mock_calls.fetch.return_value = mock_call
    mock_instance.calls.return_value = mock_calls
    
    response = client.get(f"/twilio-call-status/{room_name}")
    assert response.status_code == 200
    data = response.json()
    assert data["call_sid"] == "mock_call_sid"
    assert "status" in data