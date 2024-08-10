from loguru import logger
from sys import stderr
from datetime import datetime
from abc import ABC
from fake_useragent import UserAgent

from general_settings import GLOBAL_NETWORK


def get_user_agent():
    # Get User Agent
    user_agent = UserAgent()
    return user_agent.random


class PriceImpactException(Exception):
    pass


class BlockchainException(Exception):
    pass


class BlockchainExceptionWithoutRetry(Exception):
    pass


class SoftwareException(Exception):
    pass


class CriticalException(Exception):
    pass


class SoftwareExceptionWithoutRetry(Exception):
    pass


# While not used but may in future
class SoftwareExceptionWithRetries(Exception):
    pass


# While not used but may in future
class InsufficientBalanceException(Exception):
    pass


class Logger(ABC):
    def __init__(self):
        self.logger = logger
        self.logger.remove()
        logger_format = "<cyan>{time:HH:mm:ss}</cyan> | <level>" "{level: <8}</level> | <level>{message}</level>"
        self.logger.add(stderr, format=logger_format)
        date = datetime.today().date()
        self.logger.add(f"./data/logs/{date}.log", rotation="500 MB", level="INFO", format=logger_format)

    def logger_msg(self, account_name, address, msg, type_msg: str = 'info'):
        from config import ACCOUNT_NAMES
        class_name = self.__class__.__name__
        software_chain = GLOBAL_NETWORK
        acc_index = '1/1'
        if account_name:
            account_index = ACCOUNT_NAMES.index(account_name) + 1
            acc_index = f"{account_index}/{len(ACCOUNT_NAMES)}"

        if account_name is None and address is None:
            info = f'[Attack machine] | {software_chain} | {class_name} |'
        elif account_name is not None and address is None:
            info = f'[{acc_index}] | [{account_name}] | {software_chain} | {class_name} |'
        else:
            info = f'[{acc_index}] | [{account_name}] | {address} | {software_chain} | {class_name} |'
        if type_msg == 'info':
            self.logger.info(f"{info} {msg}")
        elif type_msg == 'error':
            self.logger.error(f"{info} {msg}")
        elif type_msg == 'success':
            self.logger.success(f"{info} {msg}")
        elif type_msg == 'warning':
            self.logger.warning(f"{info} {msg}")
        elif type_msg == 'debug':
            self.logger.debug(f"{info} {msg}")


class RequestClient(ABC):
    def __init__(self, client):
        self.client = client

    async def make_request(self, method: str = 'GET', url: str = None, headers: dict = None, params: dict = None,
                           data: str = None, json: dict = None):

        headers = (headers or {}) | {'User-Agent': get_user_agent()}
        async with self.client.session.request(method=method, url=url, headers=headers, data=data,
                                               params=params, json=json) as response:
            try:
                data = await response.json()

                if response.status == 200:
                    return data
                raise SoftwareException(
                    f"Bad request to {self.__class__.__name__} API. "
                    f"Response status: {response.status}. Response: {await response.text()}")
            except Exception as error:
                raise SoftwareException(
                    f"Bad request to {self.__class__.__name__} API. "
                    f"Response status: {response.status}. Response: {await response.text()} Error: {error}")
