import io
import os
import sys
import json
import random
import string
import asyncio
import functools
import traceback
import msoffcrypto
import pandas as pd
from typing import Union

from getpass import getpass
from termcolor import cprint
from python_socks import ProxyError
from asyncio.exceptions import TimeoutError
from aiohttp import ClientResponseError
from msoffcrypto.exceptions import DecryptionError, InvalidKeyError
from aiohttp.client_exceptions import ClientProxyConnectionError, ClientHttpProxyError

from general_settings import (
    SLEEP_TIME_MODULES,
    SLEEP_TIME_RETRY,
    MAXIMUM_RETRY,
    WALLETS_TO_WORK, MNEMONIC, GLOBAL_NETWORK, WITNESS_TYPE,
    EXCEL_PASSWORD,
    EXCEL_PAGE_NAME, EXCEL_FILE_PATH,
    DATABASE_PATH, DATABASE_CACHE_PATH
)

from bitcoinlib.mnemonic import Mnemonic
from bitcoinlib.wallets import wallet_create_or_open, HDKey, Wallet
from bitcoinlib.keys import sign


async def sleep(self, min_time=SLEEP_TIME_MODULES[0], max_time=SLEEP_TIME_MODULES[1]):
    duration = random.randint(min_time, max_time)
    print()
    self.logger_msg(*self.client.acc_info, msg=f"💤 Sleeping for {duration} seconds")
    await asyncio.sleep(duration)


# Process wallets from Excel book
async def get_wallets(wallet_names: list, wallet_keys: list) -> list:
    if WALLETS_TO_WORK == 0:
        accounts_data = zip(wallet_names, wallet_keys, [ids + 1 for ids, _ in enumerate(wallet_names)])
    elif MNEMONIC:
        accounts_data = [wallet_names[0], wallet_keys[0], 1]
    elif isinstance(WALLETS_TO_WORK, int):
        accounts_data = zip([wallet_names[WALLETS_TO_WORK - 1]], [wallet_keys[WALLETS_TO_WORK - 1]], [WALLETS_TO_WORK])

    elif isinstance(WALLETS_TO_WORK, tuple):
        account_names = [wallet_names[i - 1] for i in WALLETS_TO_WORK]
        accounts = [wallet_keys[i - 1] for i in WALLETS_TO_WORK]
        acc_ids = [acc_id for acc_id in WALLETS_TO_WORK]
        accounts_data = zip(account_names, accounts, acc_ids)

    elif isinstance(WALLETS_TO_WORK, list):
        range_count = range(WALLETS_TO_WORK[0], WALLETS_TO_WORK[1] + 1)
        account_names = [wallet_names[i - 1] for i in range_count]
        accounts = [wallet_keys[i - 1] for i in range_count]
        acc_ids = [acc_id for acc_id in range_count]
        accounts_data = zip(account_names, accounts, acc_ids)
    else:
        accounts_data = []

    accounts_data = list(accounts_data)

    return accounts_data


# Provide imported wallets to normal type bitcoin wallet
async def normalize_import_wallets(wallet_names: list, wallet_keys: list, proxies: list, db_password: str) -> tuple:
    # Get imported wallets from Excel data
    accounts = await get_wallets(wallet_names, wallet_keys)

    # Set database directory
    bcl_database_dir = os.path.join(DATABASE_PATH, 'bitcoinlib.sqlite')
    bcl_database_cache_dir = os.path.join(DATABASE_CACHE_PATH, 'bitcoinlib_cache.sqlite')

    # Set database uri
    database_uri = 'sqlite:///' + bcl_database_dir
    database_cache_uri = 'sqlite:///' + bcl_database_cache_dir

    bitcoin_wallets = []

    # MNEMONIC NOT WORKING NOW!
    if MNEMONIC:
        exit(1)
        # Import using mnemonic
        main_account_name = accounts[0]
        main_mnemonic = accounts[1]
        # Check normalize mnemonic
        try:
            main_mnemonic = Mnemonic().sanitize_mnemonic(main_mnemonic)
        except Warning:
            cprint(f'\nBad MNEMONIC phrase, check accounts_data.xlsx', color='light_red')
            exit(1)
        # Create bitcoin wallet or open if exist
        main_wallet = wallet_create_or_open(main_account_name, keys=main_mnemonic,
                                            witness_type=WITNESS_TYPE,
                                            network=GLOBAL_NETWORK,
                                            # scheme='single',
                                            db_uri=database_uri,
                                            db_cache_uri=database_cache_uri,
                                            # db_password=db_password
                                            )
        print(main_wallet.get_key().address)
        print("MNEMONIC NOT WORKING NOW!")
        exit(1)
        hdkey = HDKey.from_seed(main_mnemonic, network=GLOBAL_NETWORK)
        wallet = wallet_create_or_open(
            name='Mnemonic Wallet', network=GLOBAL_NETWORK,
            keys=hdkey.wif()
        )
        new_key = wallet.new_key("Input", 0)
        print(new_key)
        print(wallet.utxos_update())
        print(wallet.info(detail=3))
        print(wallet.addresslist())

        # print(main_wallet.new_account())
        print(wallet.accounts())
        exit(1)

        # Protect for mnemonic accounts data
        if isinstance(WALLETS_TO_WORK, Union[list, tuple]):
            if isinstance(WALLETS_TO_WORK, list):
                wallets_range = [i + 1 for i in range(WALLETS_TO_WORK[1])]
            else:
                wallets_range = [WALLETS_TO_WORK[0], WALLETS_TO_WORK[1]]
        else:
            wallets_range = [WALLETS_TO_WORK]
        for account_id in wallets_range:
            account_name = f'Account_{account_id}'
            # Get key from mnemonic path in wallets range
            # wallet_key = main_wallet.key_for_path(f"m/44'/0'/0'/0/{account_id-1}")
            # wallet_key = main_wallet.key_for_path([0, account_id - 1])
            wallet_key = wallet_create_or_open(account_name, keys=account_key,
                                               witness_type=WITNESS_TYPE, network=GLOBAL_NETWORK,
                                               # account_id=account_id,
                                               # scheme='single',
                                               # db_password=db_password
                                               ).get_key()

            bitcoin_wallets.append((account_id, account_name, wallet_key, proxies[account_id - 1]))
    else:
        for account in accounts:
            # account_name = account[0] + '_single'
            account_name = account[0]
            account_key = account[1]
            account_id = account[2]

            # Create bitcoin wallet or open if exist
            wallet = wallet_create_or_open(account_name, keys=account_key,
                                           witness_type=WITNESS_TYPE, network=GLOBAL_NETWORK,
                                           # account_id=account_id,
                                           scheme='single',
                                           db_uri=database_uri,
                                           db_cache_uri=database_cache_uri,
                                           # db_password=db_password
                                           )
            # Test working sign message
            # await signature_process(wallet)

            bitcoin_wallets.append((account_id, account_name, wallet, proxies[account_id - 1]))

    # Set up client ids for each wallet
    client_ids = await client_ids_process(bitcoin_wallets)
    return bitcoin_wallets, client_ids


async def signature_process(wallet: Wallet):
    message = "message"

    wallet_key = wallet.get_key()
    wif = wallet_key.wif
    k = HDKey.from_wif(wif)
    print(k.private_hex)
    print(k.info())
    byte_data = message.encode('utf-8')

    signature = sign(byte_data, k)
    print(signature.public_key)
    print(signature.hex())
    print(signature.secret)
    print(signature.as_der_encoded().hex())


# Get wallets data from Excel book
def get_accounts_data():
    # Database manage data files
    database_erase()
    try:
        decrypted_data = io.BytesIO()
        with open(EXCEL_FILE_PATH, 'rb') as file:
            if EXCEL_PASSWORD:
                cprint('⚔️ Enter the password degen', color='light_blue')
                password = getpass()
                office_file = msoffcrypto.OfficeFile(file)

                try:
                    office_file.load_key(password=password)
                except msoffcrypto.exceptions.DecryptionError:
                    cprint('\n⚠️ Incorrect password to decrypt Excel file! ⚠️', color='light_red', attrs=["blink"])
                    raise DecryptionError('Incorrect password')

                try:
                    office_file.decrypt(decrypted_data)
                except msoffcrypto.exceptions.InvalidKeyError:
                    cprint('\n⚠️ Incorrect password to decrypt Excel file! ⚠️', color='light_red', attrs=["blink"])
                    raise InvalidKeyError('Incorrect password')

                except msoffcrypto.exceptions.DecryptionError:
                    cprint('\n⚠️ Set password on your Excel file first! ⚠️', color='light_red', attrs=["blink"])
                    raise DecryptionError('Excel file without password!')

                office_file.decrypt(decrypted_data)

                try:
                    wb = pd.read_excel(decrypted_data, sheet_name=EXCEL_PAGE_NAME)
                except ValueError as error:
                    cprint('\n⚠️ Wrong page name! Please check EXCEL_PAGE_NAME ⚠️', color='light_red', attrs=["blink"])
                    raise ValueError(f"{error}")
            else:
                try:
                    wb = pd.read_excel(file, sheet_name=EXCEL_PAGE_NAME)
                except ValueError as error:
                    cprint('\n⚠️ Wrong page name! Please check EXCEL_PAGE_NAME ⚠️', color='light_red', attrs=["blink"])
                    raise ValueError(f"{error}")

            accounts_data = {}
            for index, row in wb.iterrows():
                account_name = row["Name"]
                private_key = row["Private Key"]
                proxy = row["Proxy"]
                cex_address = row['CEX address']
                accounts_data[int(index) + 1] = {
                    "account_number": account_name,
                    "private_key": private_key,
                    "proxy": proxy,
                    "cex_wallet": cex_address,
                }

            acc_name, priv_key, proxy, cex_wallet = [], [], [], []
            for k, v in accounts_data.items():
                acc_name.append(v['account_number'] if isinstance(v['account_number'], (int, str)) else None)
                priv_key.append(v['private_key'])
                proxy.append(v['proxy'] if isinstance(v['proxy'], str) else None)
                cex_wallet.append(v['cex_wallet'] if isinstance(v['cex_wallet'], str) else None)

            acc_name = [str(item) for item in acc_name if item is not None]
            proxy = [item for item in proxy if item is not None]
            okx_wallet = [item for item in cex_wallet if item is not None]

            if EXCEL_PASSWORD:
                return acc_name, priv_key, proxy, okx_wallet, password
            else:
                return acc_name, priv_key, proxy, okx_wallet, None
    except (DecryptionError, InvalidKeyError, DecryptionError, ValueError) as error:
        sys.exit()

    except ImportError as error:
        print(error)
        cprint(f'\nAre you sure about EXCEL_PASSWORD in general_settings.py?', color='light_red')
        sys.exit()

    except Exception as error:
        cprint(f'\nError in <get_accounts_data> function! Error: {error}\n', color='light_red')
        sys.exit()


# Manage database data and URI
def database_erase():
    type_db_path = 'data/services/type_db.json'

    # Check exist file type_db.json
    if not os.path.exists(type_db_path):
        # Create file with begin value
        data = {'mnemonic': MNEMONIC}
        with open(type_db_path, 'w') as file:
            json.dump(data, file, indent=4)
    else:
        # Read file
        with open(type_db_path, 'r') as file:
            try:
                data = json.load(file)
            except json.JSONDecodeError:
                data = {}

        # Check if file is empty
        if not data:
            delete_databases()
            # Create file with begin value
            data = {'mnemonic': MNEMONIC}
            with open(type_db_path, 'w') as file:
                json.dump(data, file, indent=4)
            return

    # Check value for 'mnemonic'
    if data.get('mnemonic') is not MNEMONIC:
        delete_databases()

        # Change value 'mnemonic'
        data['mnemonic'] = MNEMONIC

        # Write JSON file
        with open(type_db_path, 'w') as file:
            json.dump(data, file, indent=4)


def delete_databases():
    # Set database directory
    bcl_database_dir = os.path.join(DATABASE_PATH, 'bitcoinlib.sqlite')
    bcl_database_cache_dir = os.path.join(DATABASE_CACHE_PATH, 'bitcoinlib_cache.sqlite')

    # Check database exist and delete
    if os.path.exists(bcl_database_dir):
        os.remove(bcl_database_dir)

    # Check database exist and delete
    if os.path.exists(bcl_database_cache_dir):
        os.remove(bcl_database_cache_dir)


# Generate client_id
async def generate_unique_client_id(existing_ids: set, length=16):
    characters = string.ascii_lowercase + string.digits
    while True:
        new_id = ''.join(random.choice(characters) for _ in range(length))
        if new_id not in existing_ids:
            return new_id


# Основная функция
async def client_ids_process(bitcoin_wallets: list[tuple[int, str, Wallet, str]]):
    # File path
    client_ids_path = 'data/services/client_ids.json'

    # Check exist and is empty file client_ids.json
    if os.path.exists(client_ids_path) and os.path.getsize(client_ids_path) > 0:
        with open(client_ids_path, 'r') as file:
            client_dict = json.load(file)
    else:
        client_dict = {}

    # Get no duplicate all client ids
    existing_ids = set(client_dict.values())

    # Check exist client id for each wallet address
    for wallet in bitcoin_wallets:
        address = wallet[2].get_key().address
        if address not in client_dict:
            # Generate new client id
            new_id = await generate_unique_client_id(existing_ids)
            client_dict[address] = new_id
            existing_ids.add(new_id)

    # Write update data into file
    with open(client_ids_path, 'w') as file:
        json.dump(client_dict, file, indent=4)
    return client_dict


def helper(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        from modules.interfaces import (
            PriceImpactException, BlockchainException, SoftwareException, SoftwareExceptionWithoutRetry,
            BlockchainExceptionWithoutRetry, CriticalException
        )

        attempts = 0
        stop_flag = False
        infinity_flag = False
        no_sleep_flag = False
        try:
            while attempts <= MAXIMUM_RETRY and not infinity_flag:
                try:
                    return await func(self, *args, **kwargs)
                except (
                        PriceImpactException, BlockchainException, SoftwareException, SoftwareExceptionWithoutRetry,
                        BlockchainExceptionWithoutRetry, ValueError, ClientProxyConnectionError,
                        TimeoutError, ClientHttpProxyError, ProxyError, ClientResponseError, CriticalException, KeyError
                ) as err:
                    error = err
                    attempts += 1

                    msg = f'{error} | Try[{attempts}/{MAXIMUM_RETRY + 1}]'

                    if isinstance(error, KeyError):
                        stop_flag = True
                        msg = f"Setting '{error}' for this module is not exist in software!"

                    elif 'rate limit' in str(error) or '429' in str(error):
                        msg = f'Rate limit exceeded. Will try again in 5 min...'
                        await asyncio.sleep(300)
                        no_sleep_flag = True

                    elif isinstance(error, (
                            ClientProxyConnectionError, TimeoutError, ClientHttpProxyError, ProxyError,
                            ClientResponseError
                    )):
                        self.logger_msg(
                            *self.client.acc_info,
                            msg=f"Connection to RPC is not stable. Will try again in 30 sec...",
                            type_msg='warning'
                        )
                        await asyncio.sleep(30)
                        attempts -= 1
                        no_sleep_flag = True

                    elif isinstance(error, CriticalException):
                        raise error

                    elif isinstance(error, asyncio.exceptions.TimeoutError):
                        error = 'Connection to RPC is not stable'
                        await self.client.change_rpc()
                        msg = f'{error} | Try[{attempts}/{MAXIMUM_RETRY + 1}]'

                    elif isinstance(error, (SoftwareExceptionWithoutRetry, BlockchainExceptionWithoutRetry)):
                        stop_flag = True
                        msg = f'{error}'

                    elif isinstance(error, BlockchainException):
                        if 'insufficient funds' not in str(error):
                            self.logger_msg(
                                self.client.account_name,
                                None, msg=f'Maybe problem with node: {self.client.rpc}', type_msg='warning')
                            await self.client.change_rpc()

                    self.logger_msg(self.client.account_name, None, msg=msg, type_msg='error')

                    if stop_flag:
                        break

                    if attempts > MAXIMUM_RETRY and not infinity_flag:
                        self.logger_msg(
                            self.client.account_name, None,
                            msg=f"Tries are over, software will stop module\n", type_msg='error'
                        )
                    else:
                        if not no_sleep_flag:
                            await sleep(self, *SLEEP_TIME_RETRY)

                except Exception as error:
                    attempts += 1
                    msg = f'Unknown Error. Description: {error} | Try[{attempts}/{MAXIMUM_RETRY + 1}]'
                    self.logger_msg(self.client.account_name, None, msg=msg, type_msg='error')
                    traceback.print_exc()

                    if attempts > MAXIMUM_RETRY and not infinity_flag:
                        self.logger_msg(
                            self.client.account_name, None,
                            msg=f"Tries are over, software will stop module\n", type_msg='error'
                        )
        finally:
            await self.client.session.close()
        return False

    return wrapper
