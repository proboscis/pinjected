from dataclasses import dataclass

from google import genai
from google.auth.credentials import Credentials

from pinjected import IProxy

@dataclass
class GenAIAuthClient:
    """Authentication client for Google Gen AI with Vertex AI support."""

    credentials: Credentials
    project_id: str
    location: str

    def create_client(self) -> genai.Client: ...

genai_auth_client_adc: IProxy[GenAIAuthClient]
genai_auth_client: IProxy[GenAIAuthClient]
genai_location: IProxy[str]
genai_client: IProxy[genai.Client]
genai_model_name: IProxy[str]
