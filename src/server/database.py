from datetime import datetime, timedelta
from typing import List, Optional

import motor.motor_asyncio

from .api.starling_api import (
    get_main_accounts_from_starling,
    api_get_transactions_between,
    get_token_for_type_name,
)
from .models.account import StarlingMainAccountsSchema
from .models.transaction import StarlingTransactionSchema
from .secrets import username, password

MONGO_DETAILS = f"mongodb+srv://{username}:{password}@cluster0.mzv8p.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

db = client.starling_client

accounts_collection = db.get_collection("accounts")
transactions_collection = db.get_collection("transactions")


# = ROUTE METHODS ====================================================================================


async def retrieve_accounts() -> List[StarlingMainAccountsSchema]:
    """Retrieve all accounts present in the database."""
    # if no accounts in db or force update
    main_accounts = await get_main_accounts_from_starling()
    await accounts_collection.drop()
    await accounts_collection.insert_many(account_helper(main_accounts))
    return main_accounts


async def retrieve_transactions_for_account(
    type_name: str,
    account_name: str,
) -> List[StarlingTransactionSchema]:
    """Get transactions from all Starling accounts, update the database, and return them."""

    new_transactions = await get_new_transactions(account_name, type_name)
    transactions_collection.drop()  # FIXME REMOVE THIS!! debug only
    await transactions_collection.insert_many(transaction_helper(new_transactions))

    return new_transactions


# = HELPERS ==========================================================================================


def account_helper(main_accounts: List[StarlingMainAccountsSchema]) -> List[dict]:
    """Convert main_accounts into mongodb-insertable objects."""
    return [
        {
            "type_name": main_account.type_name,
            "accounts": [
                {
                    "id": account.accountUid,
                    "name": account.name,
                    "type": account.accountType,
                    "currency": account.currency,
                    "createdAt": account.createdAt,
                    "defaultCategory": account.defaultCategory,
                }
                for account in main_account.accounts
            ],
        }
        for main_account in main_accounts
    ]


def transaction_helper(transactions: List[StarlingTransactionSchema]) -> List[dict]:
    """Convert transactions into mongodb-insertable objects."""
    return [
        {
            "_id": t.feedItemUid,
            "transactionTime": t.transactionTime,
            "counterPartyName": t.counterPartyName,
            "direction": t.direction,
            "sourceAmount": {
                "currency": t.sourceAmount.currency,
                "minorUnits": t.sourceAmount.minorUnits,
            },
            "reference": t.reference,
            "status": t.status,
        }
        for t in transactions
    ]


async def get_account_for_type_and_account_name(
    type_name: str, account_name: str
) -> Optional[dict]:
    main_account = await accounts_collection.find_one({"type_name": {"$eq": type_name}})
    try:
        return next(
            account
            for account in main_account["accounts"]
            if account["name"] == account_name
        )
    except:
        return None


async def get_new_transactions(account_name, type_name):
    default_interval_days = 7
    end_date = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    start_date = (datetime.now() - timedelta(days=default_interval_days)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    token = get_token_for_type_name(type_name)
    account = await get_account_for_type_and_account_name(type_name, account_name)
    if token and account:
        new_transactions = await api_get_transactions_between(
            token=token,
            account_uid=account.get("id"),
            default_category_id=account.get("defaultCategory"),
            start_date=start_date,
            end_date=end_date,
        )
    else:
        new_transactions = []
    return new_transactions
