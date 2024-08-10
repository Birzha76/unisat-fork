from modules import Unisat
from modules.client import get_client
from general_settings import GLOBAL_NETWORK
from config import DB_PASSWORD

from bitcoinlib.wallets import Wallet


async def mint_runes(account_id: int, wallet_name: str, wallet: Wallet, proxy: str, client_id: str):
    client = await get_client(account_id, wallet_name, wallet, client_id, DB_PASSWORD, GLOBAL_NETWORK, proxy)
    return await Unisat(client).mint_runes()


async def mint_inscribes(account_id: int, wallet_name: str, wallet: Wallet, proxy: str, client_id: str):
    client = await get_client(account_id, wallet_name, wallet, client_id, DB_PASSWORD, GLOBAL_NETWORK, proxy)
    return await Unisat(client).mint_inscribes()


async def show_account_info(account_id: int, wallet_name: str, wallet: Wallet, proxy: str, client_id: str):
    client = await get_client(account_id, wallet_name, wallet, client_id, DB_PASSWORD, GLOBAL_NETWORK, proxy)
    return await Unisat(client).show_account_info()
