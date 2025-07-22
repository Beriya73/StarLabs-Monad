from web3 import Web3

KURU_API_URL = "https://api.kuru.io"

# Преобразуем все адреса в checksum
ROUTER_CONTRACT = Web3.to_checksum_address("0xc816865f172d640d93712C68a7E1F83F3fA63235")
PRICE_CALCULATOR_ADDRESS = Web3.to_checksum_address("0x24ddc1c2f7dfe7a3482f5da937bfcc2373c1368f")  # Контракт-калькулятор

# Token addresses
SHMON_CONTRACT = Web3.to_checksum_address("0x3a98250F98Dd388C211206983453837C8365BDc1")
DAK_CONTRACT = Web3.to_checksum_address("0x0f0bdebf0f83cd1ee3974779bcb7315f9808c714")
USDT_CONTRACT = Web3.to_checksum_address("0x88b8E2161DEDC77EF4ab7585569D2415a1C1055D")
USDC_CONTRACT = Web3.to_checksum_address("0xf817257fed379853cde0fa4f97ab987181b1e5ea")
CHOG_CONTRACT = Web3.to_checksum_address("0xe0590015a873bf326bd645c3e1266d4db41c4e6b")

MON_POOLS = {
    "USDC": Web3.to_checksum_address("0xd3af145f1aa1a471b5f0f62c52cf8fcdc9ab55d3"),
    "DAK": Web3.to_checksum_address("0x94b72620e65577de5fb2b8a8b93328caf6ca161b"),
    "SHMON": Web3.to_checksum_address("0x3109f8d6425a3f0c1ea26e711b873d8663e13181"),
    "CHOG": Web3.to_checksum_address("0x277bf4a0aac16f19d7bf592feffc8d2d9a890508"),
    "YAKI":Web3.to_checksum_address("0xd5c1dc181c359f0199c83045a85cd2556b325de0"),
}
# Available tokens for swaps
AVAILABLE_TOKENS = {
    "MON": {
        "name": "MON",
        "address": "0x0000000000000000000000000000000000000000",  # Native token doesn't have an address
        "decimals": 18,
        "native": True,
    },
    "SHMON": {
        "name": "SHMON",
        "address": SHMON_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "DAK": {
        "name": "DAK",
        "address": DAK_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "CHOG": {
        "name": "CHOG",
        "address": CHOG_CONTRACT,
        "decimals": 18,
        "native": False,
    },
    "USDC": {
        "name": "USDC",
        "address": USDC_CONTRACT,
        "decimals": 6,
        "native": False,
    },
}

# ABIs
ABI = {
    "router": [
        {
            "inputs": [
                {
                    "internalType": "address[]",
                    "name": "_marketAddresses",
                    "type": "address[]"
                },
                {
                    "internalType": "bool[]",
                    "name": "_isBuy",
                    "type": "bool[]"
                },
                {
                    "internalType": "bool[]",
                    "name": "_nativeSend",
                    "type": "bool[]"
                },
                {
                    "internalType": "address",
                    "name": "_debitToken",
                    "type": "address"
                },
                {
                    "internalType": "address",
                    "name": "_creditToken",
                    "type": "address"
                },
                {
                    "internalType": "uint256",
                    "name": "_amount",
                    "type": "uint256"
                },
                {
                    "internalType": "uint256",
                    "name": "_minAmountOut",
                    "type": "uint256"
                }
            ],
            "name": "anyToAnySwap",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "_amountOut",
                    "type": "uint256"
                }
            ],
            "stateMutability": "payable",
            "type": "function"
        },
{
                "inputs":[
                    {
                        "internalType":"address",
                        "name":"",
                        "type":"address"
                    }
                ],
                "name":"verifiedMarket",
                "outputs":[
                    {
                        "internalType":"uint32",
                        "name":"pricePrecision",
                        "type":"uint32"
                    },
                    {
                        "internalType":"uint96",
                        "name":"sizePrecision",
                        "type":"uint96"
                    },
                    {
                        "internalType":"address",
                        "name":"baseAssetAddress",
                        "type":"address"
                    },
                    {
                        "internalType":"uint256",
                        "name":"baseAssetDecimals",
                        "type":"uint256"
                    },
                    {
                        "internalType":"address",
                        "name":"quoteAssetAddress",
                        "type":"address"
                    },
                    {
                        "internalType":"uint256",
                        "name":"quoteAssetDecimals",
                        "type":"uint256"
                    },
                    {
                        "internalType":"uint32",
                        "name":"tickSize",
                        "type":"uint32"
                    },
                    {
                        "internalType":"uint96",
                        "name":"minSize",
                        "type":"uint96"
                    },
                    {
                        "internalType":"uint96",
                        "name":"maxSize",
                        "type":"uint96"
                    },
                    {
                        "internalType":"uint256",
                        "name":"takerFeeBps",
                        "type":"uint256"
                    },
                    {
                        "internalType":"uint256",
                        "name":"makerFeeBps",
                        "type":"uint256"
                    }
                ],
                "stateMutability":"view",
                "type":"function"
            },
    ],
    "calculator":[        {
            "inputs":[
                {
                    "internalType":"address[]",
                    "name":"route",
                    "type":"address[]"
                },
                {
                    "internalType":"bool[]",
                    "name":"isBuy",
                    "type":"bool[]"
                }
            ],
            "name":"calculatePriceOverRoute",
            "outputs":[
                {
                    "internalType":"uint256",
                    "name":"",
                    "type":"uint256"
                }
            ],
            "stateMutability":"view",
            "type":"function"
        },
    ],
    "token": [
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "account", "type": "address"}
            ],
            "name": "balanceOf",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "spender", "type": "address"},
                {"internalType": "uint256", "name": "amount", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
        {
            "inputs": [
                {"internalType": "address", "name": "owner", "type": "address"},
                {"internalType": "address", "name": "spender", "type": "address"},
            ],
            "name": "allowance",
            "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ],
}
