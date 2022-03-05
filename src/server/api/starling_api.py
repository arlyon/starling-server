""" starling_api.py

    Functions to access the Starling public API.
"""

import os
from typing import List
from typing import Type, TypeVar, Any

import httpx
from config_path import ConfigPath
from pydantic import parse_obj_as

from server.models.account import StarlingAccountsSchema, StarlingMainAccountsSchema

T = TypeVar("T")


async def api_get_accounts(token: str) -> StarlingAccountsSchema:
    return await get(token, "/accounts", None, StarlingAccountsSchema)


async def get(
    token: str, path: str, params: dict = None, return_type: Type[T] = Any
) -> T:
    """Get an api call."""
    API_BASE_URL = "https://api.starlingbank.com/api/v2"

    headers = {"Authorization": f"Bearer {token}", "User-Agent": "python"}
    url = f"{API_BASE_URL}{path}"

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, params=params)
            r.raise_for_status()
        except httpx.HTTPError as e:
            print(str(e))
            raise Exception(e)
        if return_type is not None:
            return parse_obj_as(return_type, r.json())
        else:
            return r.json()


def read_tokens_from_file_system() -> List[dict]:
    """Return a list of Starling access tokens read from the file system."""
    tokens = []
    config_path = ConfigPath("starling_server", "rjlyon.com", ".json")
    tokens_folder = config_path.saveFolderPath() / "tokens"
    tokens_files = os.listdir(tokens_folder)
    for type_name in tokens_files:
        file_path = tokens_folder / type_name
        file = open(file_path, "r")
        token = file.read().strip()
        tokens.append({"type_name": type_name, "token": token})

    return tokens


async def get_main_accounts_from_starling() -> List[StarlingMainAccountsSchema]:
    result = []
    tokens = read_tokens_from_file_system()

    for token_dict in tokens:
        type_name = token_dict.get("type_name")
        token = token_dict.get("token")
        accounts = await api_get_accounts(token)
        result.append(
            StarlingMainAccountsSchema(type_name=type_name, accounts=accounts.accounts)
        )

    return result