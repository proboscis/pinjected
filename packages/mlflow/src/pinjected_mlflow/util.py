import asyncio
import time
from os import environ
from pathlib import Path
from random import randint, random
from threading import Event

import mlflow
from google.auth import default as google_auth_default, impersonated_credentials
from google.auth.transport.requests import Request as AuthRequest
from mlflow import ActiveRun

from pinjected import instance

"""
I believe that the reason why this works on the job is that
job has some GCP SA in the environment
"""

# pinjected-reviewer: ignore

def authorize_mlflow(mlflow_client_id) -> None:
    """Create token to access ailab-mlflow via OAuth Identification
    NOTE:
    The expiration is 1 hour so that you MUST re-create access token regularly.
    Strongly recommend calling this method just before write logs to mlflow.
    https://github.com/ScruffyProdigy/google-auth-library-python/blob/master/samples/cloud-client/snippets/idtoken_from_impersonated_credentials.py
    """
    target_audience = mlflow_client_id
    scopes = [  # https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login#--scopes
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/cloud-platform",
        "https://www.googleapis.com/auth/sqlservice.login",
    ]
    source_credentials, project_id = google_auth_default(default_scopes=scopes)  # gcloud auth application-default login
    service_account = f"ailab-mlflow@cyberagent-050.iam.gserviceaccount.com"
    credentials = impersonated_credentials.Credentials(source_credentials=source_credentials,
                                                       target_principal=service_account,
                                                       target_scopes=scopes)
    id_token = impersonated_credentials.IDTokenCredentials(target_credentials=credentials,
                                                           target_audience=target_audience,
                                                           include_email=True)
    id_token.refresh(AuthRequest())
    environ["MLFLOW_TRACKING_TOKEN"] = id_token.token
    assert environ["MLFLOW_TRACKING_TOKEN"] is not None, "Failed to create token"


@instance
async def mlflow_authentication_session(mlflow_client_id: str) -> None:
    authenticated = Event()

    def task():
        while True:
            authorize_mlflow(mlflow_client_id)
            authenticated.set()
            time.sleep(30 * 60)

    import threading
    thread = threading.Thread(target=task, daemon=True)
    thread.start()
    await asyncio.to_thread(authenticated.wait)


@instance
async def mlflow(mlflow_authentication_session, mlflow_tracking_uri):
    # the session is unused but required for keeping mlflow alive
    import mlflow
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    return mlflow


@instance
def _test_log_mlflow(mlflow):
    with mlflow.start_run():
        mlflow.log_metric("accuracy", random(), step=1)
