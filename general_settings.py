GLOBAL_NETWORK = 'bitcoin'         # Choice network Bitcoin [bitcoin, mainnet, testnet]
WITNESS_TYPE = 'legacy'            # Choice type wallet Bitcoin [legacy, segwit, p2sh-segwit]
SOFTWARE_MODE = 0                  # 0 - Sync process accounts / 1 - Async process accounts
ACCOUNTS_IN_STREAM = 5             # Count process accounts for async launch
WALLETS_TO_WORK = 1          # Range or constant accounts for process

'------------------------------------------------SLEEP CONTROL---------------------------------------------------------'
SLEEP_MODE = True                 # Включает сон после каждого модуля и аккаунта
SLEEP_TIME_MODULES = (150, 300)    # (минимум, максимум) секунд | Время сна между модулями.
SLEEP_TIME_ACCOUNTS = (150, 300)   # (минимум, максимум) секунд | Время сна между аккаунтами.

'------------------------------------------------RETRY CONTROL---------------------------------------------------------'
MAXIMUM_RETRY = 5                  # Количество повторений при ошибках
SLEEP_TIME_RETRY = (30, 60)         # (минимум, максимум) секунд | Время сна после очередного повторения

'------------------------------------------------PROXY CONTROL---------------------------------------------------------'
USE_PROXY = True                   # Включает использование прокси

'------------------------------------------------PROXY CONTROL---------------------------------------------------------'
MAIN_PROXY = ''  # log:pass@ip:port, прокси для обращения к API бирж. По умолчанию
# - localhost

'------------------------------------------------SECURE DATA-----------------------------------------------------------'

# EXCEL AND GOOGLE INFO
# For Mnemonic False, the fields in Excel data are standard [Name, Private Key, Proxy, CEX address]
# For Mnemonic True Private Key filed Mnemonic data

EXCEL_PASSWORD = True  # Password for Excel book
MNEMONIC = False  # Flag for use Mnemonic or no
EXCEL_PAGE_NAME = "BITCOIN_MNEMONIC" if MNEMONIC else "BITCOIN"  # Page name in Excel book
EXCEL_FILE_PATH = "./data/accounts_data.xlsx"  # Можете не изменять, если устраивает дефолтное расположение таблицы
DATABASE_PATH = './data/services'  # Database directory path
DATABASE_CACHE_PATH = './data/services'  # Database cache directory path

# OTHER DATA

# Unisat api key get on https://developer.unisat.io/account
UNISAT_API_KEY = ""
