from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import boto3

if TYPE_CHECKING:
    from mypy_boto3_connect import ConnectClient

    from flare.config import FlareConfig

logger = logging.getLogger(__name__)


def start_voice_call(
    incident_id: str,
    config: FlareConfig,
    *,
    connect_client: ConnectClient | None = None,
) -> str | None:
    """Place an outbound call via Amazon Connect.

    Passes *incident_id* as a contact attribute so the contact flow
    can retrieve the RCA from DynamoDB.  Returns the Connect contact ID
    on success, or ``None`` if the call fails (logged, never raised).
    """
    if connect_client is None:
        connect_client = boto3.client("connect")

    try:
        response = connect_client.start_outbound_voice_contact(
            DestinationPhoneNumber=config.oncall_phone,
            ContactFlowId=config.connect_contact_flow_id,
            InstanceId=config.connect_instance_id,
            SourcePhoneNumber=config.connect_phone_number,
            Attributes={"incident_id": incident_id},
        )
        contact_id: str = response["ContactId"]
        logger.info(
            "Outbound call initiated: contact_id=%s, incident_id=%s",
            contact_id,
            incident_id,
        )
        return contact_id
    except Exception:
        logger.exception("Failed to start outbound voice call for %s", incident_id)
        return None
