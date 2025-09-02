from typing import Any, Dict
from google.oauth2.credentials import Credentials
from pinjected import IProxy

default_gcp_scopes: Any
__design__: Any

gcp_service_account_dict_from_file: IProxy[Dict[str, Any]]
gcp_credentials_from_file: IProxy[Credentials]
gcp_credentials_from_dict: IProxy[Credentials]
gcp_credentials_from_env: IProxy[Credentials]
gcp_project_id_from_dict: IProxy[str]
gcp_project_id_from_env: IProxy[str]
