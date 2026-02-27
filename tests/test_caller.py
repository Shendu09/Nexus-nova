from __future__ import annotations

from unittest.mock import Mock

from flare.caller import start_voice_call
from flare.config import FlareConfig


def test_start_voice_call_success(voice_config: FlareConfig):
    mock_connect = Mock()
    mock_connect.start_outbound_voice_contact.return_value = {
        "ContactId": "contact-abc-123"
    }

    result = start_voice_call(
        "incident-001", voice_config, connect_client=mock_connect
    )

    assert result == "contact-abc-123"
    mock_connect.start_outbound_voice_contact.assert_called_once_with(
        DestinationPhoneNumber="+15559876543",
        ContactFlowId="test-flow-id",
        InstanceId="test-instance-id",
        SourcePhoneNumber="+15551234567",
        Attributes={"incident_id": "incident-001"},
    )


def test_start_voice_call_failure(voice_config: FlareConfig):
    mock_connect = Mock()
    mock_connect.start_outbound_voice_contact.side_effect = Exception("Connect error")

    result = start_voice_call(
        "incident-001", voice_config, connect_client=mock_connect
    )

    assert result is None
