import asyncio
import random
import time

from eth_account import Account
from loguru import logger
from primp import AsyncClient
from web3 import AsyncWeb3
from decimal import Decimal
from typing import Dict, List, Optional, Union, Tuple
from web3.contract import AsyncContract
from src.utils.config import Config
from src.utils.constants import RPC_URL,EXPLORER_URL
from .constants import (KURU_API_URL,
                        ROUTER_CONTRACT,
                        PRICE_CALCULATOR_ADDRESS,
                        SHMON_CONTRACT,
                        DAK_CONTRACT,
                        USDT_CONTRACT,
                        USDC_CONTRACT,
                        CHOG_CONTRACT,
                        AVAILABLE_TOKENS,
                        MON_POOLS,
                        ABI,
                        )


class Kuru:
    def __init__(self, account_index: int, proxy: str, private_key: str, config: Config, session: AsyncClient):
        self.account_index = account_index
        self.private_key = private_key
        self.config = config
        self.account: Account = Account.from_key(private_key=private_key)
        self.web3 = AsyncWeb3(
            AsyncWeb3.AsyncHTTPProvider(RPC_URL, request_kwargs={"proxy": f"http://{proxy}" if proxy else None})
        )
        self.router_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(ROUTER_CONTRACT), abi=ABI["router"]
        )
        self.calculator_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(PRICE_CALCULATOR_ADDRESS), abi=ABI["calculator"]
        )

    async def execute(self):
        """
        Execute Kuru swap operations based on configuration settings.
        Performs several random swaps according to the settings.
        If SWAP_ALL_TO_MONAD option is enabled, exchanges all tokens to MON.
        """
        logger.info(f"[{self.account_index}] Starting Kuru swap operations")

        # Check if we need to swap all tokens to MON
        if (
            hasattr(self.config.KURU, "SWAP_ALL_TO_MONAD")
            and self.config.KURU.SWAP_ALL_TO_MONAD
        ):
            logger.info(
                f"[{self.account_index}] SWAP_ALL_TO_MONAD is enabled, swapping all tokens to MON"
            )
            await self.swap_all_to_monad()
            return

        # Get balances of all available tokens
        token_balances = {}
        for symbol, token_info in AVAILABLE_TOKENS.items():
            balance = await self.get_token_balance(self.account.address, token_info)
            token_balances[symbol] = balance
            logger.info(f"[{self.account_index}] Balance of {symbol}: {balance}")

        # # Check if we have any tokens other than MON
        # non_mon_tokens = []
        # for symbol, balance in token_balances.items():
        #     if symbol != "MON" and balance > 0.01:
        #         non_mon_tokens.append(symbol)
        #
        # # If no tokens other than MON, buy a random token
        # if not non_mon_tokens and token_balances.get("MON", 0) > 0.01:
        #     await self._buy_random_token(token_balances["MON"])

        # Determine number of swaps to perform
        min_swaps, max_swaps = self.config.FLOW.NUMBER_OF_SWAPS
        num_swaps = random.randint(min_swaps, max_swaps)

        logger.info(f"[{self.account_index}] Will perform {num_swaps} swaps")

        # Perform the specified number of swaps
        for swap_num in range(1, num_swaps + 1):
            logger.info(f"[{self.account_index}] Executing swap {swap_num}/{num_swaps}")

            # Update token balances for accurate selection
            for symbol, token_info in AVAILABLE_TOKENS.items():
                balance = await self.get_token_balance(self.account.address, token_info)
                token_balances[symbol] = balance

            # Choose random token pair for swap
            token_from, token_to, amount = await self._select_random_token_pair(
                token_balances
            )

            if not token_from or not token_to:
                logger.warning(
                    f"[{self.account_index}] No suitable tokens found for swap {swap_num}. Skipping."
                )
                continue

            logger.info(
                f"[{self.account_index}] Swap {swap_num}: {token_from} -> {token_to}, "
                f"amount: {amount}"
            )

            # Check if amount is sufficient for swap
            if amount <= 0.01:
                logger.warning(
                    f"[{self.account_index}] Amount too small for swap {swap_num}. Skipping."
                )
                continue

            # Execute swap
            swap_result = await self.swap(token_from, token_to, amount)

            if swap_result["success"]:
                logger.success(
                    f"[{self.account_index}] Swap {swap_num} completed successfully: "
                    f"{swap_result['amount_in']} {swap_result['from_token']} -> "
                    f"{swap_result['expected_out']} {swap_result['to_token']}"
                )

                # If not the last swap, pause before next one
                if swap_num < num_swaps:
                    pause_time = random.randint(
                        self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[0],
                        self.config.SETTINGS.RANDOM_PAUSE_BETWEEN_ACTIONS[1],
                    )
                    logger.info(
                        f"[{self.account_index}] Pausing for {pause_time} seconds before next swap"
                    )
                    await asyncio.sleep(pause_time)
            else:
                logger.error(
                    f"[{self.account_index}] Swap {swap_num} failed: {swap_result.get('error', 'Unknown error')}"
                )

                # If swap failed, pause before next attempt
                if swap_num < num_swaps:
                    pause_time = random.randint(
                        self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[0],
                        self.config.SETTINGS.PAUSE_BETWEEN_ATTEMPTS[1],
                    )
                    logger.info(
                        f"[{self.account_index}] Pausing for {pause_time} seconds before next swap attempt"
                    )
                    await asyncio.sleep(pause_time)

        logger.success(
            f"[{self.account_index}] Completed all {num_swaps} Kuru swap operations"
        )

    async def swap_all_to_monad(self):
        """
        Swaps all tokens to MON (native token).
        Handles different token thresholds based on value.
        """
        target_token = AVAILABLE_TOKENS["MON"]
        logger.info(f"[{self.account_index}] 🔄 Swapping all tokens to MON")

        # Define minimum thresholds for different tokens
        # These values are in token units, not MON value
        token_thresholds = {
            "WMON": 0.01,  # Стандартный порог для WMON
            "WETH": 0.0001,  # Меньший порог для WETH из-за высокой стоимости
            "WSOL": 0.001,  # Очень низкий порог для WSOL
            "USDT": 0.01,  # Стандартный порог для стейблкоинов
            "WBTC": 0.000001,  # Низкий порог для WBTC из-за высокой стоимости
            "MAD": 0.01,  # Стандартный порог
            "USDC": 0.01,  # Стандартный порог для стейблкоинов
        }

        # Default threshold for any token not in the list
        default_threshold = 0.0000001

        # Iterate through all available tokens
        for symbol, token in AVAILABLE_TOKENS.items():
            # Skip MON, as it's the target token
            if token["native"]:
                continue

            # Get token balance
            balance = await self.get_token_balance(self.account.address, token)

            # Get threshold for this token
            threshold = token_thresholds.get(symbol, default_threshold)

            # If balance is too small, skip
            if balance <= threshold:
                logger.info(
                    f"[{self.account_index}] Skipping {symbol} - balance too low: {balance} (threshold: {threshold})"
                )
                continue

            # Log balances before swap
            mon_balance_before = await self.get_token_balance(
                self.account.address, target_token
            )
            logger.info(
                f"[{self.account_index}] Balance {symbol} before swap: {balance}"
            )
            logger.info(
                f"[{self.account_index}] Balance MON before swap: {mon_balance_before}"
            )

            try:
                # Special case: WMON -> MON via withdraw
                if symbol == "WMON":
                    amount_wei = int(balance * (10 ** token["decimals"]))
                    result = await self._withdraw_wmon_to_mon(amount_wei)
                else:
                    # For other tokens use regular swap
                    result = await self.swap(symbol, "MON", balance)

                if result["success"]:
                    logger.success(
                        f"[{self.account_index}] Successfully swapped {balance} {symbol} to MON. "
                        f"TX: {EXPLORER_URL}{result['tx_hash']}"
                    )
                else:
                    logger.error(
                        f"[{self.account_index}] Failed to swap {symbol} to MON: {result.get('error', 'Unknown error')}"
                    )

            except Exception as e:
                logger.error(
                    f"[{self.account_index}] Error swapping {symbol} to MON: {str(e)}"
                )

            # Log balances after swap
            token_balance_after = await self.get_token_balance(
                self.account.address, token
            )
            mon_balance_after = await self.get_token_balance(
                self.account.address, target_token
            )
            logger.info(
                f"[{self.account_index}] Balance {symbol} after swap: {token_balance_after}"
            )
            logger.info(
                f"[{self.account_index}] Balance MON after swap: {mon_balance_after}"
            )

            # Pause between swaps
            await asyncio.sleep(random.randint(2, 5))

        logger.success(f"[{self.account_index}] 🎉 All tokens have been swapped to MON")
        return True

    async def swap(self, token_from: str, token_to: str, amount: float, slippage: float = 1.0) -> Dict:

        for retry in range(self.config.SETTINGS.ATTEMPTS):
            try:
                # 1. Получаем информацию о токенах
                token_a = AVAILABLE_TOKENS[token_from]
                token_b = AVAILABLE_TOKENS[token_to]

                # 2. Получаем достоверную информацию о рынке (структура + цена)
                market_info = await self.get_market_info(token_from, token_to)

                # 3. Вычисляем параметры
                address_a_cs = self.web3.to_checksum_address(token_a["address"])
                address_b_cs = self.web3.to_checksum_address(token_b["address"])
                is_buy_flag = (address_a_cs == market_info["quote_asset"])
                is_native_send_flag = token_a.get("native", False)
                pool_address = market_info.get("pool_address")
                amount_in_decimal = Decimal(str(amount))

                # --- ФИНАЛЬНЫЙ, ПРАВИЛЬНЫЙ РАСЧЕТ OUTPUT ---
                if is_buy_flag:  # Отдаем Quote, покупаем Base
                    # Нам нужен курс Quote -> Base
                    price_to_use = market_info["price_quote_to_base"]
                else:  # Отдаем Base, получаем Quote
                    # Нам нужен курс Base -> Quote
                    price_to_use = market_info["price_base_to_quote"]

                # Выход ВСЕГДА равен количеству на курс
                output_decimal = amount_in_decimal * price_to_use

                min_amount_out_wei = int(output_decimal * (Decimal('100') - Decimal(str(slippage))) / Decimal('100') * (
                            Decimal('10') ** token_b["decimals"]))
                amount_in_wei = int(amount_in_decimal * (Decimal('10') ** token_a["decimals"]))

                # 4. Approve (если нужно)
                if not token_a.get("native"):
                    await self.approve_token(token_a, amount_in_wei, ROUTER_CONTRACT)

                # 5. Собираем транзакцию ТОЛЬКО Legacy-типа
                tx_params = {
                    "from": self.account.address,
                    "nonce": await self.web3.eth.get_transaction_count(self.account.address, "latest"),
                    "gasPrice": await self.web3.eth.gas_price,
                    "value": amount_in_wei if token_a.get("native") else 0
                }
                #
                # print(f"pool_address: {[pool_address]}")
                # print(f"is_buy_flag: {[is_buy_flag]}")
                # print(f"is_native_send_flag: {[is_native_send_flag]}")
                # print(f"Токен A: {address_a_cs}")
                # print(f"Токен B {address_b_cs}")
                # print(f"Amount in Wei: {amount_in_wei}")
                # print(f"Min_amount_out_wei: {min_amount_out_wei}")

                # 6. Готовим и отправляем
                swap_function = self.router_contract.functions.anyToAnySwap(
                    [pool_address], [is_buy_flag], [is_native_send_flag],
                    address_a_cs, address_b_cs,
                    amount_in_wei, min_amount_out_wei
                )
                tx_to_estimate = await swap_function.build_transaction(tx_params)

                # 2. Оцениваем газ для ПОЛНОЙ транзакции
                estimated_gas = await self.estimate_gas(tx_to_estimate)

                # 3. Добавляем рассчитанный газ в параметры
                tx_params['gas'] = estimated_gas

                # 4. Строим финальную транзакцию со всеми параметрами, включая 'gas'
                final_tx = await swap_function.build_transaction(tx_params)
                signed_tx = self.account.sign_transaction(final_tx)
                # return {"success": True}
                tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)

                receipt = await self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

                if receipt["status"] == 1:
                    return {
                        "success": True,
                        "tx_hash": tx_hash.hex(),
                        "amount_in": float(amount_in_decimal),  # Сумма, которую отправили
                        "from_token": token_from,  # Токен, который отправили
                        "to_token": token_to,  # Токен, который получили
                        "expected_out": float(output_decimal)  # Ожидаемая сумма на выходе
                    }
                else:
                    logger.error(f"[{self.account_index}] Транзакция провалилась (status 0).")
                    continue
            except Exception as e:
                logger.error(
                    f"[{self.account_index}] Ошибка в попытке {retry + 1}/{self.config.SETTINGS.ATTEMPTS}: {e}")
                if retry < self.config.SETTINGS.ATTEMPTS - 1:
                    pause = random.randint(5, 10)
                    await asyncio.sleep(pause)
        return {"success": False, "error": "Max retry attempts reached"}

    async def get_gas_params(self) -> Dict[str, int]:
        """Get current gas parameters from the network."""
        latest_block = await self.web3.eth.get_block("latest")
        base_fee = latest_block["baseFeePerGas"]
        max_priority_fee = await self.web3.eth.max_priority_fee
        max_fee = base_fee + max_priority_fee
        return {
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

    async def estimate_gas(self, transaction: dict) -> int:
        """Estimate gas for transaction and add a buffer."""
        try:
            estimated = await self.web3.eth.estimate_gas(transaction)
            return int(estimated * 1.1)
        except Exception as e:
            logger.warning(
                f"[{self.account_index}] Error estimating gas: {e}. Using default gas limit"
            )
            raise e

    async def check_allowance(
            self, token_address: str, spender_address: str, amount_wei: int
    ) -> bool:
        """Check if allowance is sufficient for token."""
        token_contract = await self.get_token_contract(token_address)
        current_allowance = await token_contract.functions.allowance(
            self.account.address, spender_address
        ).call()
        return current_allowance >= amount_wei

    async def get_token_contract(
            self, token_address: str, abi: Dict = None
    ) -> AsyncContract:
        """
        Get token contract instance

        Args:
            token_address: Token contract address
            abi: ABI to use (defaults to token ABI)

        Returns:
            Contract: Token contract instance
        """
        if abi is None:
            abi = ABI["token"]

        return self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address), abi=abi
        )

    async def get_market_info(self, token_from_name: str, token_to_name: str) -> dict:
        pool_address_str = MON_POOLS.get(token_to_name if token_from_name == "MON" else token_from_name)
        if not pool_address_str:
            raise ValueError(f"Пул для {token_from_name}/{token_to_name} не найден в MON_POOLS.")

        pool_address_cs = self.web3.to_checksum_address(pool_address_str)
        market_data = await self.router_contract.functions.verifiedMarket(pool_address_cs).call()
        base_asset = self.web3.to_checksum_address(market_data[2])
        quote_asset = self.web3.to_checksum_address(market_data[4])

        # --- ЗАПРАШИВАЕМ ОБА КУРСА ---
        price_base_to_quote_wei = await self.calculator_contract.functions.calculatePriceOverRoute([pool_address_cs],
                                                                                                   [True]).call()
        price_quote_to_base_wei = await self.calculator_contract.functions.calculatePriceOverRoute([pool_address_cs],
                                                                                                   [False]).call()

        return {
            "pool_address": pool_address_cs,
            "base_asset": base_asset,
            "quote_asset": quote_asset,
            "price_base_to_quote": Decimal(price_base_to_quote_wei) / Decimal(10 ** 18),
            "price_quote_to_base": Decimal(price_quote_to_base_wei) / Decimal(10 ** 18)
        }

    async def approve_token(self, token: dict, amount_wei: int, spender_address: str):
        spender_cs = self.web3.to_checksum_address(spender_address)
        token_contract = self.web3.eth.contract(address=self.web3.to_checksum_address(token['address']),
                                                abi=ABI["token"])
        allowance = await token_contract.functions.allowance(self.account.address, spender_cs).call()
        if allowance < amount_wei:
            logger.info(f"[{self.account_index}] Выполняем approve для {token['name']}...")
            approve_func = token_contract.functions.approve(spender_cs, 2 ** 256 - 1)
            tx_params = {
                'from': self.account.address,
                'nonce': await self.web3.eth.get_transaction_count(self.account.address, "latest"),
                'gasPrice': await self.web3.eth.gas_price
            }
            tx_to_estimate = await approve_func.build_transaction(tx_params)
            tx_params['gas'] = await self.estimate_gas(tx_to_estimate)
            final_tx = await approve_func.build_transaction(tx_params)
            signed_tx = self.account.sign_transaction(final_tx)
            tx_hash = await self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            await self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            logger.success(f"[{self.account_index}] Approve для {token['name']} успешен.")

    async def get_token_balance(self, wallet_address: str, token: dict) -> float:
        wallet_address_cs = self.web3.to_checksum_address(wallet_address)
        if token.get("native"):
            balance_wei = await self.web3.eth.get_balance(wallet_address_cs)
            return float(self.web3.from_wei(balance_wei, "ether"))
        else:
            token_contract = self.web3.eth.contract(address=self.web3.to_checksum_address(token["address"]),
                                                    abi=ABI["token"])
            balance_wei = await token_contract.functions.balanceOf(wallet_address_cs).call()
            return float(balance_wei) / (10 ** token["decimals"])

    async def estimate_gas(self, transaction: dict) -> int:
        return int(await self.web3.eth.estimate_gas(transaction) * 1.3)

    async def _buy_random_token(self, mon_balance: float):
        """
        Buy a random token using a percentage of MON balance

        Args:
            mon_balance: Current MON balance
        """
        # Get percent of balance to use from config
        min_percent, max_percent = self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP
        percent = random.uniform(min_percent, max_percent)

        # Calculate amount to use (percent of MON balance)
        amount = mon_balance * (percent / 100)

        # Choose a random token to buy (excluding MON and WMON)
        possible_tokens = [
            symbol
            for symbol in AVAILABLE_TOKENS.keys()
            if symbol not in ["MON", "WMON"]
        ]

        if not possible_tokens:
            logger.warning(f"[{self.account_index}] No tokens available to buy")
            return

        token_to_buy = random.choice(possible_tokens)

        logger.info(
            f"[{self.account_index}] Buying {token_to_buy} with {amount} MON ({percent:.2f}% of balance)"
        )

        # Execute the swap
        result = await self.swap("MON", token_to_buy, amount)

        if result["success"]:
            logger.success(
                f"[{self.account_index}] Successfully bought {result['expected_out']} {token_to_buy} "
                f"with {amount} MON. TX: {EXPLORER_URL}{result['tx_hash']}"
            )
        else:
            logger.error(
                f"[{self.account_index}] Failed to buy {token_to_buy}: "
                f"{result.get('error', 'Unknown error')}"
            )

    async def _select_random_token_pair(
            self, token_balances: Dict[str, float]
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        Выбирает случайный токен для покупки за MON.
        Обмен всегда будет MON -> Другой токен.

        Args:
            token_balances: Словарь с балансами токенов.

        Returns:
            Кортеж ("MON", token_to, amount) или (None, None, 0) в случае неудачи.
        """
        # 1. Исходный токен всегда MON
        token_from = "MON"
        mon_balance = token_balances.get(token_from, 0.0)

        # 2. Проверяем, достаточно ли MON для обмена
        # Поставим минимальный порог, например, 0.01 MON
        if mon_balance < 0.01:
            logger.warning(
                f"[{self.account_index}] Баланс MON ({mon_balance}) слишком мал для обмена. Пропускаем."
            )
            return None, None, 0

        # 3. Выбираем случайный токен для покупки (не должен быть MON)
        possible_tokens_to = [
            symbol for symbol in AVAILABLE_TOKENS.keys() if symbol != "MON"
        ]

        if not possible_tokens_to:
            logger.warning(
                f"[{self.account_index}] Нет доступных токенов для покупки за MON."
            )
            return None, None, 0

        token_to = random.choice(possible_tokens_to)
        logger.info(f"[{self.account_index}] ===> Выбран токен для покупки: {token_to}")
        # 4. Определяем сумму для обмена (процент от баланса MON из конфига)
        min_percent, max_percent = self.config.FLOW.PERCENT_OF_BALANCE_TO_SWAP
        percent = random.uniform(min_percent, max_percent)
        amount = mon_balance * (percent / 100)

        logger.info(
            f"[{self.account_index}] Выбран обмен: {amount:.6f} {token_from} -> {token_to} "
            f"({percent:.2f}% от баланса MON)"
        )

        return token_from, token_to, amount
