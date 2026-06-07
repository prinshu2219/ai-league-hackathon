"""
Secrets loading — local .env vs AWS Secrets Manager (production).

Local:  python-dotenv loads .env
Prod:   boto3 fetches JSON from AWS Secrets Manager at startup
"""

import json
import os
import logging

logger = logging.getLogger(__name__)


def load_secrets() -> None:
    """
    Load API keys into os.environ.
    Called once at app startup before any LLM client is created.
    """
    app_env = os.getenv("APP_ENV", "development")

    if app_env == "production" and os.getenv("AWS_SECRET_NAME"):
        _load_from_aws(os.getenv("AWS_SECRET_NAME"))
    else:
        from dotenv import load_dotenv
        load_dotenv()
        logger.info("Secrets loaded from .env (development mode)")


def _load_from_aws(secret_name: str) -> None:
    """Fetch secrets from AWS Secrets Manager via boto3."""
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError("boto3 required for production secrets") from e

    region = os.getenv("AWS_REGION", "ap-south-1")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    secrets = json.loads(response["SecretString"])

    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if key in secrets:
            os.environ[key] = secrets[key]

    logger.info("Secrets loaded from AWS Secrets Manager: %s", secret_name)
