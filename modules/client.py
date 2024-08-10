import asyncio
from typing import Union

from aiohttp import ClientSession, TCPConnector
from aiohttp_socks import ProxyConnector
from modules.interfaces import SoftwareException, Logger, get_user_agent
from general_settings import (
    MNEMONIC
)
from bitcoinlib.wallets import Wallet, WalletTransaction, WalletError
from bitcoinlib.values import Value
from bitcoinlib.transactions import Output


class Client(Logger):
    def __init__(self, account_id: int, account_name: str | int, wallet: Wallet,  client_id: str, db_password: str,
                 network: str = "bitcoin", proxy: None | str = None):
        Logger.__init__(self)
        self.network = network
        self.token = "BTC"
        self.explorer = "https://www.blockchain.com/explorer/transactions/btc/"

        self.proxy_init = proxy
        self.session: ClientSession = ClientSession(
            connector=ProxyConnector.from_url(f"http://{proxy}", verify_ssl=False)
            if proxy else TCPConnector(verify_ssl=False)
        )
        self.user_agent = get_user_agent()

        self.request_kwargs = {"proxy": f"http://{proxy}"} if proxy else {}

        self.account_id = account_id
        self.account_name = str(account_name)
        self.wallet = wallet
        self.private_key = self.wallet.get_key().key_private
        self.address = self.wallet.get_key().address
        self.acc_info = self.account_name, self.address
        self.client_id = client_id

    # Provide to satoshi type (Value object)
    @staticmethod
    async def to_sat(amount: Union[str, int]) -> Value:
        if isinstance(amount, int):
            value_amount = Value(f'{amount} sat')
        else:
            if 'sat' in amount:
                value_amount = Value(f'{amount}')
            else:
                value_amount = Value(f'{amount} sat')
        return value_amount

    # Ge balance wallet
    async def get_balance(self) -> [float, str]:
        # self.wallet.balance()
        return self.wallet.balance_update_from_serviceprovider()

    # Send transaction with value to address
    async def send_to(self, to_address: str, amount: Union[str, int, Value], fee: Union[int, str] = "normal",
                      simulate_send: bool = False) -> bool:
        try:
            # Provide to Value type amount
            value_amount = amount
            if isinstance(amount, Union[str, int]):
                value_amount = await self.to_sat(amount)
            sat_amount = value_amount.value_sat

            # Fee maybe [low', 'normal', 'high']
            # Get balance
            balance = await self.get_balance()
            # Check balance enough
            balance_delta = balance - sat_amount - 2000
            if balance_delta <= 0:
                self.logger_msg(*self.acc_info, msg="You not enough balance BTC", type_msg='error')
                return False

            # WHILE NOT WORKING WITH MNEMONIC, BUT IT WILL BE REPAIR SOON
            if MNEMONIC:
                return
                output_arr = [(to_address, sat_amount)]
                # Create transaction object with params
                print(self.address)
                tx = self.wallet.transaction_create(output_arr, random_output_order=False)
                # print(tx.info())
                print(tx.outputs)
                if len(tx.outputs) > 1:
                    for i, tx_output in enumerate(tx.outputs):
                        if tx_output.address != to_address and tx_output.address != self.address:
                            tx.outputs[i] = Output(tx_output.value, self.address)

                print(tx.outputs)
                print(tx.info())
                return

                # Calculate transaction fees
                tx.calculate_fee()
                fee_amount = {
                    'low': 100,
                    'normal': 200,
                    'high': 400,
                }[fee]
                print(tx.fee)
                tx.fee = tx.fee + fee_amount
                print(tx.fee)

                fee_exact = tx.fee
                while 2000 <= fee_exact <= 1000:
                    fee_exact = tx.calculate_fee()
                    self.logger_msg(*self.acc_info, msg=f"Recalculate fee for transaction prev fee {tx.fee},"
                                                        f" estimate fee now {fee_exact}",
                                    type_msg='debug')
                    tx = self.wallet.transaction_create(output_arr=output_arr, fee=fee_exact)

                    await asyncio.sleep(30)

                # Check outputs addresses, because multisig by default send all btc to you wallet in depth path
                change_outputs = []
                print(tx.outputs)
                if len(tx.outputs) > 1:
                    for tx_output in tx.outputs:
                        if tx_output.address == to_address:
                            change_outputs.append(tx_output)

                # Check inputs data, for correct value for transaction
                print(tx.inputs)
                print(tx.input_total)
                input_value = sat_amount + tx.fee

                print(tx.inputs[0].value)
                tx.inputs[0].value = input_value
                number = len(output_arr)
                byte_array = number.to_bytes(1, byteorder='big')
                tx.inputs[0].output_n = byte_array
                print(tx.inputs[0].value)
                # for tx_input in tx.inputs:
                #     print(tx_input)
                #     print(tx_input.value)
                #     print(tx_input.output_n)
                #     print(hex(2))
                #     number = 2
                #     byte_array = number.to_bytes(1, byteorder='big')
                #     print(byte_array)
                #     if tx_input.address == self.address:
                #         tx_input.value = input_value
                print(tx.inputs[0].value)
                # Setup transaction params
                tx.outputs = change_output

                # Transaction Sign
                tx.sign()

                # Prepare transaction data
                tx.rawtx = tx.raw()
                tx.size = len(tx.rawtx)
                tx.calc_weight_units()
                tx.fee_per_kb = int(float(tx.fee) / float(tx.vsize) * 1000)
                tx.txid = tx.signature_hash()[::-1].hex()

                # Send transaction
                tx.send(offline=simulate_send)
            else:
                tx = self.wallet.send_to(to_address=to_address, amount=sat_amount, fee=fee, offline=simulate_send)

            tx_id = ''
            if tx.error:
                if 'txn-mempool-conflict' in str(tx.error):
                    self.logger_msg(*self.acc_info, msg="You are already send transaction,"
                                                        " check last txs through 3 minutes", type_msg='warning')
                    await asyncio.sleep(180)
                    self.wallet.transactions_update()
                    tx_id = self.wallet.transaction_last(self.address)
                elif 'Transaction not send, unknown response from service providers' in str(tx.error):
                    self.logger_msg(*self.acc_info, msg="Maybe txs already sent right now", type_msg='warning')

            print(tx.info())

            if not tx_id:
                tx_id = tx.txid

            # Wait confirmed transaction into blockchain
            tx_data = await self.wait_confirmation_transaction(tx_id=tx_id, timeout=0 if simulate_send else 600)

            if tx_data:
                self.logger_msg(*self.acc_info, msg=f'Transaction was successful: {self.explorer}{tx_data.txid}',
                                type_msg='success')
                return True
        except WalletError as error:
            # Update transaction and balance info into database
            if "UTXO's" in str(error):
                print(f'send_to: {error}')
                self.wallet.utxos_update()
                await self.send_to(to_address, amount, fee, simulate_send)
            else:
                print(f'someone error: {error}')

        return False

    # Wait confirmation transaction into Bitcoin blockchain, but only for you wallet.
    async def wait_confirmation_transaction(self, tx_id: str, timeout: int = 600,
                                            confirmations: int = 0) -> Union[bool, WalletTransaction]:
        time_step = timeout
        tx_data = False
        while time_step > 0:
            # Get transaction from Database
            tx_data = self.wallet.transaction(txid=tx_id)
            print(tx_data)

            if tx_data is None or tx_data.status == 'unconfirmed':
                self.logger_msg(*self.acc_info, msg=f"Wait getting tx: {tx_id} into blockchain", type_msg='debug')
                # Update information about transactions from blockchain
                self.wallet.transactions_update()
            elif confirmations:
                self.logger_msg(*self.acc_info, msg=f"Wait >= {confirmations} confirmations for {tx_id}"
                                                    f" into blockchain", type_msg='debug')
                # Update confirmation transactions
                self.wallet.transactions_update_confirmations()

            if tx_data:
                if confirmations and tx_data.confirmations >= confirmations:
                    return tx_data
                elif not confirmations:
                    return tx_data
            time_step -= 15
            await asyncio.sleep(15)
        return tx_data

    # While not used, but may
    async def get_token_price(self, token_name: str, vs_currency: str = 'usd') -> float:

        stables = [
            'dai',
            'tether',
            'usd-coin',
            'bridged-usdc-polygon-pos-bridge',
            'binance-usd',
            'bridged-usd-coin-base',
            'usdb',
        ]

        if token_name in stables:
            return 1.0

        await asyncio.sleep(20)  # todo поправить на 20с
        url = 'https://api.coingecko.com/api/v3/simple/price'

        params = {
            'ids': f'{token_name}',
            'vs_currencies': f'{vs_currency}'
        }

        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return float(data[token_name][vs_currency])
            elif response.status == 429:
                self.logger_msg(
                    *self.acc_info, msg=f'CoinGecko API got rate limit. Next try in 300 second', type_msg='warning')
                await asyncio.sleep(300)
            raise SoftwareException(f'Bad request to CoinGecko API: {response.status}')


# Get bitcoin wallet client
async def get_client(account_id: int, account_name: str | int, wallet: Wallet, client_id: str, db_password: str,
                     network: str, proxy: None | str) -> Client:
    return Client(account_id, account_name, wallet, client_id, db_password, network, proxy)
