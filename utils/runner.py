import asyncio
from asyncio.locks import Semaphore

from utils.tools import normalize_import_wallets
from config import ACCOUNT_NAMES, PRIVATE_KEYS, PROXIES, DB_PASSWORD
from general_settings import SOFTWARE_MODE, ACCOUNTS_IN_STREAM

from termcolor import cprint


from utils.functions import mint_runes, mint_inscribes, show_account_info
AVAILABLE_MODULES = {
    'mint_runes': mint_runes,
    'mint_inscribes': mint_inscribes,
    'show_account_info': show_account_info,
}


async def run_modules(module_name: str):
    # Check exist module name
    try:
        module = AVAILABLE_MODULES[module_name]
    except KeyError:
        cprint(f"\n{module_name} this module doesn't exist!", color='light_red')
        return False
    # Get imported bitcoin wallets
    bitcoin_wallets, client_ids = await normalize_import_wallets(ACCOUNT_NAMES, PRIVATE_KEYS, PROXIES, DB_PASSWORD)
    if SOFTWARE_MODE:
        # Async run accounts
        # Create the shared semaphore
        semaphore = asyncio.Semaphore(ACCOUNTS_IN_STREAM)
        # Create and schedule tasks
        tasks = [asyncio.create_task(run_async(semaphore, module, client_ids,
                                               bitcoin_wallet)) for bitcoin_wallet in bitcoin_wallets]
        # Gather all created tasks
        await asyncio.gather(*tasks)
    else:
        # Sync run accounts
        for bitcoin_wallet in bitcoin_wallets:
            account_id = bitcoin_wallet[0]
            wallet_name = bitcoin_wallet[1]
            wallet = bitcoin_wallet[2]
            proxy = bitcoin_wallet[3]
            client_id = client_ids[wallet.get_key().address]
            await module(account_id, wallet_name, wallet,  proxy, client_id)


async def run_async(semaphore: Semaphore, module, client_ids: dict, *args):
    # Acquire the semaphore
    async with semaphore:
        account_id = args[0]
        wallet_name = args[1]
        wallet = args[2]
        proxy = args[3]
        client_id = client_ids[wallet.get_key().address]
        await module(account_id, wallet_name, wallet, proxy, client_id)
