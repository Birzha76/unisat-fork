import base64
import json
import asyncio
import datetime
from random import randint, choice
from urllib.parse import quote

import pandas as pd

from utils.tools import helper
from modules import Logger, RequestClient, Client
from general_settings import UNISAT_API_KEY


class Unisat(Logger, RequestClient):
    def __init__(self, client: Client):
        self.client = client
        Logger.__init__(self)
        RequestClient.__init__(self, client)

    # Manage orders
    async def get_order_list(self, status: str = '', cursor: int = 0, size: int = 100):
        url = "https://api.unisat.space/inscribe-v5/order/list"

        headers = {
            'accept': 'application/json, text/plain, */*',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            "origin": "https://unisat.io",
            "referer": "https://unisat.io/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": self.client.user_agent
            # 'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Filter params
        filter_params = {
            "clientId": self.client.client_id,
            "sort": "asc",
            "receiveAddress": self.client.address
        }

        # Add status if True status maybe ['pending', 'closed', 'minted', 'inscribing']
        if status:
            filter_params['status'] = status

        # Filter params dict to str
        filter_str = json.dumps(filter_params)

        # Prepare params for request
        params = {
            'cursor': cursor,
            'size': size,
            "filter": filter_str
        }

        # Make request
        response = await self.make_request(method="GET", url=url, headers=headers, params=params)
        order_list = list(response['data']['list'])

        # If list elements >= limit size then recurse this while response with list will not be == 0
        # Also may check it with help response['data']['total'] in each response
        if len(order_list) >= size:
            new_order_list = await self.get_order_list(status=status, cursor=cursor + 1, size=size)
            order_list.extend(new_order_list)
        return order_list

    async def get_order_data(self, order_id: str):
        url = f"https://api.unisat.space/inscribe-v5/order/{order_id}"

        headers = {
            'accept': 'application/json, text/plain, */*',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            "origin": "https://unisat.io",
            "referer": "https://unisat.io/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": self.client.user_agent
            # 'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Make request
        response = await self.make_request(method="GET", url=url, headers=headers)
        return response['data']

    async def _create_order(self, fee_rate: int, action: str, **kwargs):
        headers = {
            'accept': 'application/json, text/plain, */*',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            "origin": "https://unisat.io",
            "referer": "https://unisat.io/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": self.client.user_agent
            # 'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Condition for mint runes
        if action == "runes":
            url = "https://api.unisat.space/inscribe-v5/order/create/runes-mint"

            # Prepare params request for create order mint runes
            data = {
                "clientId": self.client.client_id,
                "count": int(kwargs.get('count')),
                "feeRate": fee_rate,
                "outputValue": 546,
                "receiver": self.client.address,
                "runeId": kwargs.get('runeId'),
            }
        else:
            url = "https://api.unisat.space/inscribe-v5/order/create"

            # Prepare params request for create order mint inscribes
            data = {
                "clientId": self.client.client_id,
                "feeRate": fee_rate,
                "files": [
                    {
                        "dataURL": kwargs.get('data_url'),
                        "filename": kwargs.get('filename')
                    }
                ],
                "outputValue": 546,
                "receiver": self.client.address,
            }
        # Make request
        response = await self.make_request(method="POST", url=url, headers=headers, json=data)

        return response['data']

    async def create_order_inscribes(self, amount: int):
        # Get ticker list by default 500 limit in request
        ticker_list = await self.get_ticker_list()

        # Choice random ticker and check for opportunity mint for this ticker
        ticker = await self.choices_ticker(tickers=ticker_list, amount=amount)
        if not ticker:
            raise ValueError('Ticker not found in ticker list check create_order_inscribes')
            # self.logger_msg(*self.client.acc_info, msg=f'Ticker not found in ticker list check
            # create_order_inscribes', type_msg="error") return False

        # Get Fee rate from Unisat
        fee_rate = await self.get_estimate_fees()

        # Prepare params for request
        json_object = {"p": "brc-20", "op": "mint", "tick": ticker, "amt": f"{amount}"}
        encoded_string = await self.encode_json_to_base64(json_object)
        decoded_request_string = await self.json_to_request_string_compact(json_object)
        filename = decoded_request_string
        data_url = f"data:text/plain;charset=utf-8;base64,{encoded_string}"
        params = {
            'filename': filename,
            'data_url': data_url,
        }
        # Create order
        return await self._create_order(fee_rate=fee_rate, action='inscribes', **params)

    async def create_order_runes(self, amount: int):
        # Get runes list by default 100 limit in request
        # Check only not completed mint of runes
        runes_list = await self.get_runes_list()

        # Getting runes data and random choice rune from list
        rune_data = choice(runes_list)
        rune_id = rune_data['runeid']
        # rune_name = rune_data['rune']

        # Get Fee rate from Unisat
        fee_rate = await self.get_estimate_fees()

        # Prepare params for request
        params = {
            'count': amount,
            'runeId': rune_id
        }

        # Create order
        return await self._create_order(fee_rate=fee_rate, action='runes', **params)

    async def wait_confirmation_order(self, order_id: str, timeout: int = 60*20) -> bool:
        time_step = timeout
        while time_step >= 0:
            self.logger_msg(*self.client.acc_info, msg=f'Order ID: {order_id} | Wait confirm payment',
                            type_msg='debug')
            # Update order data
            order_data = await self.get_order_data(order_id=order_id)

            # Get and check status order
            if order_data:
                status_order = order_data['status']
                if status_order in ('inscribing', 'minted'):
                    self.logger_msg(*self.client.acc_info, msg=f'Order ID: {order_id} | Successfully confirmed',
                                    type_msg='success')
                    return True
            time_step -= 30
            await asyncio.sleep(30)
        return False

    # Manage runes
    async def get_runes_list(self, start: int = 0, limit: int = 100, depth: int = 1):
        url = f"https://open-api.unisat.io/v1/indexer/runes/info-list"

        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Prepare params for request
        params = {
            'sort': 'timestamp',
            'complete': 'no',
            'start': start,
            'limit': limit,
        }

        runes_list = []
        # Make request on given depth if request is empty then it is end list
        # Also depth the best choice less or equal 5
        if depth and depth <= 5:
            for _ in range(0, depth):
                # Make request
                response = await self.make_request(method="GET", url=url, headers=headers, params=params)
                new_runes_list = list(response['data']['detail'])
                if not new_runes_list:
                    break
                else:
                    params['start'] = start + 100
                runes_list.extend(new_runes_list)
        return runes_list

    async def get_runes_info(self, rune_id: str):
        # Encode rune id for request
        encoded_id = quote(rune_id)
        url = f"https://open-api.unisat.io/v1/indexer/runes/{encoded_id}/info"

        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Make request
        response = await self.make_request(method="GET", url=url, headers=headers)

        return response['data']

    # Get estimate fee now
    async def get_estimate_fees(self, fee_type: str = "halfHourFee"):
        # fee_type may be is [fastestFee, halfHourFee, hourFee, economyFee, minimumFee]
        url = "https://mempool.space/api/v1/fees/recommended"

        headers = {
            'accept': 'application/json, text/plain, */*',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            "origin": "https://unisat.io",
            "referer": "https://unisat.io/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": self.client.user_agent
        }

        # Make request
        response = await self.make_request(method="GET", url=url, headers=headers)
        return response[fee_type]

    # Manage tickers
    async def get_ticker_list(self, start: int = 0, limit: int = 500, depth: int = 1):
        url = f"https://open-api.unisat.io/v1/indexer/brc20/list"

        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Prepare params for request
        params = {
            'start': start,
            'limit': limit,
            # tick_filter by (8/16/24) => (4-byte/5-byte/ALL)
            'tick_filter': '8',  # 4-byte inscribes tickers now support, change this for find other tickers
        }

        ticker_list = []
        # Make request on given depth if request is empty then it is end list
        # Also depth the best choice less or equal 5
        if depth and depth <= 5:
            for _ in range(0, depth):
                # Make request
                response = await self.make_request(method="GET", url=url, headers=headers, params=params)
                new_ticker_list = list(response['data']['detail'])
                if not new_ticker_list:
                    break
                else:
                    params['start'] = start + 500
                ticker_list.extend(new_ticker_list)
        return ticker_list

    async def get_ticker_info(self, ticker: str):
        url = f"https://open-api.unisat.io/v1/indexer/brc20/{ticker}/info"

        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        response = await self.make_request(method="GET", url=url, headers=headers)
        total_minted = int(response['data']['totalMinted'])
        limit_mint = int(response['data']['max'])
        may_mint = False
        if limit_mint - total_minted > 0:
            may_mint = True

        mint_limit = int(response['data']['limit'])
        return may_mint, mint_limit

    async def choices_ticker(self, tickers: list, amount: int):
        may_mint = False
        mint_limit = amount

        # Set copy list tickers
        temp_ticker = tickers.copy()

        ticker = ''
        # Make request while opportunity mint for ticker will be not True
        while not may_mint and mint_limit <= amount:
            # Random choice ticker
            ticker = choice(temp_ticker)

            # Get Ticker info
            may_mint, mint_limit = await self.get_ticker_info(ticker=ticker)
            if not may_mint:
                temp_ticker.remove(ticker)
                duration = randint(5, 15)
                await asyncio.sleep(duration)
        return ticker

    # Account Unisat manage
    async def get_account_history(self, start: int = 0, limit: int = 100):
        url = "https://api.unisat.space/basic-v4/points/history?start=0&limit=20"

        headers = {
            # 'accept': 'application/json, text/plain, */*',
            # "accept-encoding": "gzip, deflate, br, zstd",
            # "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            # "origin": "https://unisat.io",
            # "referer": "https://unisat.io/",
            # "sec-ch-ua-mobile": "?0",
            # "sec-ch-ua-platform": '"Windows"',
            # "sec-fetch-dest": "empty",
            # "sec-fetch-mode": "cors",
            # "sec-fetch-site": "cross-site",
            # "user-agent": self.client.user_agent
            # 'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Prepare params for request
        params = {
            'start': start,
            'limit': limit,
        }

        # Make request
        response = await self.make_request(method="GET", url=url, headers=headers, params=params)
        order_list = list(response['data']['list'])
        total_orders = int(response['data']['total'])

        # If list elements >= limit size then recurse this while response with list will not be == 0
        # Also may check it with help response['data']['total'] in each response
        if len(order_list) >= limit:
            new_order_list, new_total_orders = await self.get_account_history(start=start + 100, limit=limit)
            order_list.extend(new_order_list)
            total_orders += new_total_orders
        return order_list, total_orders

    async def get_account_info(self):
        url = "https://api.unisat.space/basic-v4/base/quick_login"

        headers = {
            'accept': 'application/json, text/plain, */*',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            "origin": "https://unisat.io",
            "referer": "https://unisat.io/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": self.client.user_agent
            # 'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Prepare params for request
        params = {
            'address': self.client.address,
        }

        # Make request
        response = await self.make_request(method="POST", url=url, headers=headers, json=params)
        account_info = response['data']

        return account_info

    async def get_balance_info(self):
        url = f"https://api.unisat.space/query-v4/address/{self.client.address}/balance"

        headers = {
            'accept': 'application/json, text/plain, */*',
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,ru-RU;q=0.8,ru;q=0.7",
            'Content-Type': 'application/json',
            "origin": "https://unisat.io",
            "referer": "https://unisat.io/",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "cross-site",
            "user-agent": self.client.user_agent
            # 'Authorization': f'Bearer {UNISAT_API_KEY}',
        }

        # Make request
        response = await self.make_request(method="GET", url=url, headers=headers)
        balance_info = response['data']

        return balance_info

    # Static methods
    @staticmethod
    async def encode_json_to_base64(json_data: dict):
        # Converting a JSON object to a string with specified formatting
        json_string = json.dumps(json_data, separators=(',', ':'), ensure_ascii=False)

        # Base64 encoding of a string
        base64_bytes = base64.b64encode(json_string.encode('utf-8'))

        # Convert Base64 bytes to string
        base64_string = base64_bytes.decode('utf-8')

        return base64_string

    @staticmethod
    async def json_to_request_string_compact(json_data: dict):
        # Convert JSON object to string without spaces
        json_string = json.dumps(json_data, separators=(',', ':'))
        return json_string

    @helper
    async def mint_inscribes(self):
        # Get order list
        order_list = await self.get_order_list(status='pending')
        self.logger_msg(*self.client.acc_info, msg=f'You have {len(order_list)} orders. '
                                                   f'Check pending orders inscribes on Unisat')
        pending_orders = []

        if order_list:
            for order in order_list:
                if 'type' not in order_list:
                    if order['status'] == 'pending':
                        # Check created time
                        created_time = int(order['createTimestamp'] / 1000)
                        timestamp_now = int(datetime.datetime.now().timestamp())
                        delta_time = int(timestamp_now - created_time)
                        # if lower than 25 minutes, the best choice skip
                        if delta_time <= 60 * 25:
                            pending_orders.append(order)

        if pending_orders:
            self.logger_msg(*self.client.acc_info, msg=f'You have {len(pending_orders)} pending orders. '
                                                       f'Choice 1 order for complete mint inscribes on Unisat')
            order = pending_orders[0]
        else:
            self.logger_msg(*self.client.acc_info, msg=f'Create order for mint inscribes on Unisat')
            order = await self.create_order_inscribes(amount=1)

        pay_address = order['payAddress']
        amount = await self.client.to_sat(order['amount'])
        order_id = order['orderId']
        self.logger_msg(*self.client.acc_info, msg=f'Order ID: {order_id} | Paying {amount.str()} to {pay_address}')
        await self.client.send_to(to_address=pay_address, amount=amount, fee="high")
        return await self.wait_confirmation_order(order_id=order_id)

    @helper
    async def mint_runes(self):
        # Code realise mint runes
        order_list = await self.get_order_list(status='pending')
        self.logger_msg(*self.client.acc_info, msg=f'You have {len(order_list)} orders. '
                                                   f'Check pending orders runes on Unisat')
        pending_orders = []

        if order_list:
            for order in order_list:
                if 'type' in order and order['type'] == 'runes-mint':
                    if order['status'] == 'pending':
                        # Check created time
                        created_time = int(order['createTimestamp'] / 1000)
                        timestamp_now = int(datetime.datetime.now().timestamp())
                        delta_time = int(timestamp_now - created_time)
                        # if lower than 25 minutes, the best choice skip
                        if delta_time <= 60 * 25:
                            pending_orders.append(order)
        if pending_orders:
            self.logger_msg(*self.client.acc_info, msg=f'You have {len(pending_orders)} pending orders. '
                                                       f'Choice 1 order for complete mint runes on Unisat')
            order = pending_orders[0]
        else:
            self.logger_msg(*self.client.acc_info, msg=f'Create order for mint runes on Unisat')
            order = await self.create_order_runes(amount=1)
        pay_address = order['payAddress']
        amount = await self.client.to_sat(order['amount'])
        order_id = order['orderId']

        self.logger_msg(*self.client.acc_info, msg=f'Order ID: {order_id} | Paying {amount.str()} to {pay_address}')
        await self.client.send_to(to_address=pay_address, amount=amount, fee="high")
        return await self.wait_confirmation_order(order_id=order_id)

    @helper
    async def show_account_info(self):
        # WHILE NOT WORKING
        print("show_account_info --- WHILE NOT WORKING")
        pass
        # # Getting account history orders
        # """
        # address: "address"
        # ct: 1723225977866
        # oid: "order_id"
        # point: 1
        # type: 0
        # _id: "66b65779beab4aa3d9ee4cb5
        # """
        # account_history, total_orders = await self.get_account_history()
        #
        # # Calculate total points
        # total_points = 0
        # for history_data in account_history:
        #     point = int(history_data['point'])
        #     total_points += point
        #
        # # Getting account info from quick login
        # """
        # swapAccess: {access: false, minimumPoints: 200, passConfirmation: 0, passCount: 0, inWhiteList: false}
        # access: false
        # inWhiteList: false
        # minimumPoints: 200
        # passConfirmation: 0
        # passCount: 0
        # address: "address"
        # badgeAllRank: null
        # badgeSlot: {}
        # inscribeCount: 3
        # lockedVsat: 0
        # ogPassCount: 0
        # satsCount: 0
        # session: "8d34b448-da9c-4fc1-8cfc-d45e361109f5"
        # sessionExpire: 1723314521332
        # unisatCount: 0
        # vsat: 0
        # """
        # account_info = await self.get_account_info()
        # inscribe_count = account_info['inscribeCount']
        # badge_all_rank = account_info['badgeAllRank']
        # session = account_info['session']
        # session_expire = datetime.datetime.fromtimestamp(account_info['sessionExpire'])
        # unisat_count = account_info['unisatCount']
        #
        # # Create DataFrame
        # df = pd.DataFrame({
        #     'Session': [session, session_expire],
        #     'Inscribe Count': inscribe_count,
        #     'Unisat Count': unisat_count,
        #     'Badge All Rank': badge_all_rank,
        #     'Points': total_points,
        #     'Total Orders': total_orders
        # })
        #
        # # print table
        # print(df.to_markdown())

