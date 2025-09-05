from dataclasses import dataclass

from google import genai
from google.auth import default
from google.auth.credentials import Credentials
from loguru import logger

from pinjected import instance


@dataclass
class GenAIAuthClient:
    """Authentication client for Google Gen AI with Vertex AI support."""

    credentials: Credentials
    project_id: str
    location: str = "global"

    def create_client(self) -> genai.Client:
        """Create a Gen AI client with Vertex AI and ADC support."""
        # Use vertexai=True to enable Vertex AI mode with ADC
        client = genai.Client(
            vertexai=True,
            project=self.project_id,
            location=self.location,
            credentials=self.credentials,
        )
        logger.info(
            f"Created Gen AI client with Vertex AI mode for project {self.project_id} "
            f"in {self.location}"
        )
        return client


@instance
def genai_auth_client_adc() -> GenAIAuthClient:
    """Default Gen AI auth client using Application Default Credentials."""
    logger.info("Creating Gen AI auth client using Application Default Credentials")
    credentials, project = default()

    if not project:
        raise ValueError(
            "Could not determine GCP project ID from Application Default Credentials. "
            "Please set GOOGLE_CLOUD_PROJECT environment variable or use gcloud config."
        )

    logger.info(f"Using ADC with project: {project}")
    return GenAIAuthClient(credentials=credentials, project_id=project)


@instance
def genai_auth_client(
    genai_auth_client_adc: GenAIAuthClient,
    genai_location: str,
) -> GenAIAuthClient:
    """Gen AI authentication client - default uses ADC, can be overridden via injection."""
    # Update location from injection
    genai_auth_client_adc.location = genai_location
    return genai_auth_client_adc


@instance
def genai_location() -> str:
    """Default GCP location for Gen AI API.

    Note: Gemini 2.5 Flash Image Preview (nano-banana) is only available
    on the global endpoint, not regional endpoints.
    """
    return "global"


@instance
def genai_client(
    genai_auth_client: GenAIAuthClient,
) -> genai.Client:
    """Singleton Gen AI client with Vertex AI and ADC support."""
    client = genai_auth_client.create_client()
    logger.info(
        f"Created Gen AI client for project {genai_auth_client.project_id} "
        f"in {genai_auth_client.location}"
    )
    return client
