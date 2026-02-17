"""Configuration loaded from environment variables."""

import os


class Config:
    """Configuration loaded from environment variables."""

    # AWS
    S3_BUCKET = os.getenv("ICEBERG_S3_BUCKET")
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1e")

    # WebSocket
    WEBSOCKET_URL = os.getenv("WEBSOCKET_URL")
    WEBSOCKET_RECONNECT_DELAY = int(os.getenv("WEBSOCKET_RECONNECT_DELAY", "5"))

    # Iceberg
    ICEBERG_WAREHOUSE = f"s3://{S3_BUCKET}/warehouse" if S3_BUCKET else None

    @classmethod
    def validate(cls):
        """Validate required config."""
        if not cls.S3_BUCKET:
            msg = "ICEBERG_S3_BUCKET environment variable required"
            raise ValueError(msg)
        if not cls.WEBSOCKET_URL:
            msg = "WEBSOCKET_URL environment variable required"
            raise ValueError(msg)
