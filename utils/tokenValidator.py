import re
import aiohttp
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import logger, SUPPORTED_CHAIN_IDS, LIFI_API_URL, ACME_APP_URL, RETRY_COUNT, DEFAULT_TIMEOUT, ACME_API_KEY, ACME_URL
from handlers.auth_handler import get_user_top3
from utils.createTradingLink import create_trading_link
from utils.getTokenMarketData import fetch_and_format_token_market_data


# Regex pattern to detect if the token is an EVM contract address (42 hex characters)
EVM_CONTRACT_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Regex pattern for detecting Solana Virtual Machine (SVM) contract addresses (Base58, typically 32 bytes)
SVM_CONTRACT_ADDRESS_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

TOKEN_TEMPLATE = (
    "*{index}️ [{symbol}]({trading_link})*\n"
    " ├ Price: *{price}*\n"
    " ├ 24H: *{change_24h}*\n"
    " ├ MCap: *${mcap}*\n\n"
    #"🔄 Circulating Supply: *{circulating_supply}*\n"
)

async def validate_tokens(requested_tokens, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate requested tokens and store valid ones in user context."""
    logger.info(f"Starting token validation for user: {update.effective_user.id}")
    valid_tokens = []
    invalid_tokens = []

    for token in requested_tokens:
        logger.debug(f"Validating token: {token} - Type: {type(token).__name__}")

        if isinstance(token, str):
            logger.debug(f"Processing token as string (symbol or address): {token}")
            token_data = await fetch_token_data_from_chains(token=token)
            if token_data and "error" not in token_data:
                token_address = token_data.get("address")
                trading_link = await get_trading_link_from_top3(update, context, token_address)
                if not trading_link:
                    trading_link = await generate_trading_link(update, context, token_data)

                if trading_link:
                    token_data["tradingLink"] = trading_link
                    valid_tokens.append(token_data)
                    logger.info(f"Valid token found: {token_data['symbol']} ({token_data['address']})")
                else:
                    logger.error(f"Failed to generate trading link for token: {token}")
                    invalid_tokens.append(token)
            else:
                logger.warning(f"Invalid or missing token data for: {token}")
                invalid_tokens.append(token)

        elif isinstance(token, dict):
            logger.debug(f"Processing token object: {token}")

            # Extract values with default None
            token_address = token.get("address")
            trading_link = token.get("tradingLink")
            intent_id = token.get("intentId")

            # Check for errors and existing trading link
            if "error" not in token:
                if not trading_link:  # Generate trading link only if it doesn't exist
                    trading_link = await generate_trading_link(update, context, token, intent_id)

                if trading_link:  # If trading link was successfully created
                    token["tradingLink"] = trading_link
                    valid_tokens.append(token)
                    logger.info(f"Valid token object: {token['symbol']} ({token_address})")
                else:
                    logger.error("Failed to create trading link for token object.")
                    invalid_tokens.append(token)
            else:
                logger.warning(f"Invalid token object: {token}")
                invalid_tokens.append(token)
        else:
            logger.warning(f"Unsupported token format: {token}")
            invalid_tokens.append(token)

    logger.info(f"Validation completed. Valid tokens: {len(valid_tokens)}, Invalid tokens: {len(invalid_tokens)}")
    return valid_tokens, invalid_tokens


async def generate_trading_link(update: Update, context: ContextTypes.DEFAULT_TYPE, token_data, intent_id=None):
    """Generate a trading link using an existing or newly created intent ID."""
    logger.debug(f"Generating trading link for token: {token_data['symbol']}")
    trading_link = None  # Initialize trading_link as None

    try:
        if intent_id:
            trading_link = f"{ACME_APP_URL}/buy/{intent_id}"
            logger.debug(f"Using existing intent ID for trading link: {trading_link}")
        else:
            chain_id = token_data.get("chainId")
            token_address = token_data.get("address")
            trading_link = await create_trading_link(update, context, chain_id, token_address, "")

            logger.debug(f"Successfully created trading link: {trading_link}")

    except ValueError as e:
        logger.error(f"Error generating trading link for token {token_data['symbol']}: {e}")
        # You can raise the error or return None if you want to handle it at a higher level
        trading_link = None  # Set trading_link to None to indicate failure

    return trading_link

async def get_trading_link_from_top3(update: Update, context: ContextTypes.DEFAULT_TYPE, token_address: str):
    """
    Retrieve intent ID from the user's auth result if available.

    Args:
        update (Update): The Telegram update instance.
        context (ContextTypes.DEFAULT_TYPE): The context instance.
        token_address (str): The address of the token to look up.

    Returns:
        str or None: The intent ID if found, or None if not found or token_info_list is None.
    """
    logger.debug(f"Fetching intent ID for token: {token_address}")
    top3 = await get_user_top3(update, context)

    # Check if token_info_list is None or empty
    if not top3:
        logger.warning("Token info list is None or empty. Skipping iteration.")
        return None

    logger.debug(f"Retrieved top 3 tokens: {top3}")
    for token in top3:
        if token.get("address") == token_address:
            trading_link = token.get("tradingLink")
            logger.debug(f"Found Trading Link: {trading_link}")
            return trading_link

    logger.warning(f"No Trading Link found for token: {token_address}")
    return None

def extract_token_data(token_data):
    """Extract and validate fields from the LiFi API response."""
    #logger.debug(f"Extracting token data: {token_data}")

    try:
        symbol = token_data.get("symbol")
        name = token_data.get("name")
        logo_url = token_data.get("logoURI")
        chain_id = token_data.get("chainId")
        decimals = token_data.get("decimals")
        contract_address = token_data.get("address")
        price = token_data.get("priceUSD")

        if all([symbol, name, logo_url, chain_id, decimals, contract_address]):
            formatted_price = f"${float(price):,.{decimals}f}" if price else "N/A"
            logger.debug(f"Valid token data extracted: {symbol}, Price: {formatted_price}")
            return {
                "symbol": symbol,
                "name": name,
                "logoUrl": logo_url,
                "chain_id": chain_id,
                "decimals": decimals,
                "contract_address": contract_address,
                "price": formatted_price,
            }

        logger.warning("Incomplete token data.")
        return {"error": "Incomplete token data."}
    except KeyError as e:
        logger.exception(f"Missing field during extraction: {e}")
        return {"error": "Incomplete token data."}


async def fetch_and_format_token_data(token, username, index):
    """
    Fetches market data for a token and formats it into a text template.

    Args:
    - token (dict): The token data containing 'symbol', 'chain_id', 'contract_address', 'decimals', and 'tradingLink'.
    - username (str): The username to be displayed in the message.
    - index (int): The index or rank of the token.

    Returns:
    - tuple: Formatted text, trading link for the token, and the button.
    """
    symbol = token.get('symbol', '').strip().upper()
    chain_id = token.get('chainId')
    contract_address = token.get('address') or token.get('tokenAddress')
    decimals = token.get('decimals')
    intent_id = token.get('intentId','')
    trading_link = token.get('tradingLink', '')

    if intent_id and not trading_link:  # Generate trading link only if it doesn't exist
        trading_link = f"{ACME_APP_URL}/buy/{intent_id}"
    
    if not chain_id or not contract_address or not trading_link:
        raise ValueError(f"Missing required token data for {symbol}.")

    token_market_data = await fetch_and_format_token_market_data(contract_address, chain_id, decimals)

    # Determine the appropriate index symbol
    if index == 0:
        index_symbol = "✅"  # For the first token
    elif index == 1:
        index_symbol = "🥇"
    elif index == 2:
        index_symbol = "🥈"
    elif index == 3:
        index_symbol = "🥉"
    else:
        index_symbol = f"{index + 1}️⃣"  # Use numeric emojis for tokens beyond the top 3

    # Format the trading card text
    trading_card_text = TOKEN_TEMPLATE.format(
        index=index_symbol,
        symbol=symbol,
        trading_link=trading_link,
        price=token_market_data.get('price', 'N/A'),
        change_24h=token_market_data.get('change_24h', 'N/A'),
        mcap=token_market_data.get('mcap', 'N/A'),
    )

    # Create the button label based on index
    button_label = f"Buy {symbol}" if index == 0 else symbol
    button = InlineKeyboardButton(button_label, url=trading_link)

    return trading_card_text, button  # Return both text and button

async def fetch_token_data_from_chains(token: str, chain_id: Optional[str] = None):
    """
    Fetch token data across chains from LiFi API, returning the one with the highest market cap.

    Args:
        token (str): The symbol or address of the token.
        chain_id (str, optional): Specific chain ID for targeted fetching. Defaults to None.

    Returns:
        dict or None: Highest market cap token data if available, otherwise None.
    """
    # Determine if the token is a contract address (EVM or SVM) or a symbol
    if EVM_CONTRACT_ADDRESS_PATTERN.match(token):
        # Token is an EVM contract address; remove Solana from supported chains
        acme_param = {"symbol": token}
        chains = {cid: name for cid, name in SUPPORTED_CHAIN_IDS.items() if name.lower() != "solana"}
    elif SVM_CONTRACT_ADDRESS_PATTERN.match(token):
        # Token is an SVM contract address; limit to Solana-specific chain ID
        acme_param = {"symbol": token}
        chains = [("1151111081099710", "solana")]
    else:
        # Token is a symbol; convert to uppercase and query all supported chains
        acme_param = {"symbol": token.upper()}
        chains = SUPPORTED_CHAIN_IDS.items()

    # Convert 'solana' to its specific chain ID if chain_id is provided
    chain_id = '1151111081099710' if chain_id == 'solana' else chain_id

    # First, attempt to fetch data from Acme using either contract address or symbol
    acme_data = await fetch_tokens_from_acme(**acme_param, chain_id=chain_id)
    if acme_data:
        logger.debug(f"Token data for {token} found on Acme.")
        return acme_data

    # If not found on Acme, fetch from LiFi across chains
    logger.info(f"Fetching token data for {token} across specified chains.")
    tokens_data = await fetch_tokens_across_chains_from_lifi(token, chains)
    if not tokens_data:
        logger.warning(f"No token data found across chains for token: {token}")
        return None

    # Add market cap data for tokens, if available
    tokens_with_mcap = await fetch_market_cap_for_tokens(tokens_data)
    if not any("mcap" in token for token in tokens_with_mcap):
        logger.warning(f"No market cap found for token: {token} across any chain.")
        return None

    # Select and return the token data with the highest market cap
    highest_mcap_token = select_highest_mcap(tokens_with_mcap)

    # Register the highest market cap token with Acme
    logger.info(f"Registering token with highest market cap: {highest_mcap_token.get('symbol', 'Unknown')}")
    return await register_tokens_on_acme([highest_mcap_token])
    
async def fetch_tokens_from_acme(symbol: str, chain_id: Optional[str] = None, skip: int = 0, take: int = 5):
    """
    Fetch tokens from Acme with optional chainId and retry logic.

    Args:
        symbol (str): The symbol of the token (e.g., "ETH").
        chain_id (str, optional): The chain ID to filter tokens. Defaults to None.
        skip (int): Number of items to skip for pagination. Defaults to 0.
        take (int): Number of items to take for pagination. Defaults to 5.

    Returns:
        dict or None: The response JSON on success, or None if the operation fails.
    """
    base_url = f"{ACME_URL}/checkout/currency/get-all-currencies"
    params = {"symbol": symbol, "skip": skip, "take": take}
    if chain_id:
        params["chainId"] = chain_id

    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                logger.debug(f"Fetching tokens from Acme: {base_url} {params}")
                async with session.get(base_url, params=params, headers={"X-API-KEY": ACME_API_KEY}) as response:
                    logger.debug(f"Attempt {attempt + 1}: Fetching tokens, Response status: {response.status}")
                    if response.status == 200:
                        data = await response.json()
                        # Check if 'data' is a key in the response and it is a non-empty list
                        if 'data' in data and isinstance(data['data'], list) and data['data']:
                            logger.debug(f"Tokens fetched from Acme: {data}")
                            return data['data'][0]  # Return the first token if it exists

                        # Log if 'data' is an empty list
                        logger.warning("No tokens found in the response from Acme.")
                    elif response.status == 404:
                        logger.info(f"Token {symbol} not found on Acme.")
                        break
            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: Client error occurred: {e}")
    return None


async def fetch_tokens_across_chains_from_lifi(token_symbol: str, chains: list[tuple]):
    """Fetch token data across chains from LiFi, filtering for valid results."""
    tokens_data = []
    tasks = [
        fetch_token_data_from_lifi(token_symbol, chain_id, platform)
        for chain_id, platform in chains
    ]
    lifi_responses = await asyncio.gather(*tasks, return_exceptions=True)

    for response in lifi_responses:
        if isinstance(response, dict) and 'symbol' in response:
            tokens_data.append(response)

    logger.info(f"LiFi returned {len(tokens_data)} valid tokens for symbol {token_symbol}")
    return tokens_data


async def fetch_token_data_from_lifi(token_symbol: str, chain_id: str, platform: str):
    """
    Fetch token data from LiFi for a specific chain. Return token data if found; log and continue if not.
    """
    url = f"{LIFI_API_URL}/token"
    params = {"chain": chain_id, "token": token_symbol}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    token_data = await response.json()
                    if token_data and 'symbol' in token_data:
                        token_data.update({"chain_id": chain_id, "platform_name": platform})
                        logger.info(f"Token data found on LiFi for {token_symbol} on chain {chain_id}.")
                        return token_data
                elif response.status != 404:
                    logger.warning(f"LiFi request failed with status {response.status} for {token_symbol} on chain {chain_id}")
        except aiohttp.ClientError as e:
            logger.error(f"Network error with LiFi for {token_symbol} on {chain_id}: {e}")
    return None


async def fetch_market_cap_for_tokens(tokens_data):
    """Fetch market cap data for each token from CoinGecko and add to token data."""
    tasks = [fetch_mcap(token["address"], token["chain_id"]) for token in tokens_data]
    mcap_responses = await asyncio.gather(*tasks, return_exceptions=True)

    tokens_with_mcap = []
    for token, mcap_data in zip(tokens_data, mcap_responses):
        if isinstance(mcap_data, float):
            token["mcap"] = mcap_data
            tokens_with_mcap.append(token)
            logger.info(f"Market cap for {token['symbol']} found: {mcap_data}")
        else:
            logger.warning(f"Market cap not available for {token['symbol']} on chain {token['chain_id']}")
    return tokens_with_mcap


async def fetch_mcap(contract_address: str, chain_id: str) -> float:
    """Fetch the market cap for a given token contract address from CoinGecko."""
    platform_id = SUPPORTED_CHAIN_IDS.get(str(chain_id), 'solana')
    url = (
        f"https://api.coingecko.com/api/v3/simple/token_price/{platform_id}"
        f"?contract_addresses={contract_address}"
        "&vs_currencies=usd&include_market_cap=true"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                contract_address_key = list(data.keys())[0]
                market_cap = data[contract_address_key].get("usd_market_cap")
                return market_cap if market_cap else None
    except aiohttp.ClientError as e:
        logger.exception(f"Failed to fetch market cap for contract address {contract_address}: {e}")
    return None


def select_highest_mcap(tokens_with_mcap):
    """Select the token with the highest market cap from the list of tokens with market cap data."""
    return max(tokens_with_mcap, key=lambda x: x["mcap"], default=None)


async def register_tokens_on_acme(tokens: list[dict]):
    """
    Register or update tokens for the DEX aggregator on Acme.
    Sanitizes tokens to ensure only required fields are sent, and converts chain ID to "solana" if needed.

    Args:
        tokens (list[dict]): List of token data dictionaries containing required fields.

    Returns:
        dict or None: The first registered token object from `currenciesLoaded` in the API response,
                      or None if registration fails.
    """
    # Determine dexAggregatorId based on chain_id presence
    dex_aggregator_id = "Jupiter" if any(token.get("chain_id") == "1151111081099710" for token in tokens) else "LiFi"

    # Sanitize tokens to include only necessary fields, with chain ID transformation
    sanitized_tokens = [
        {
            "chainId": "solana" if token.get("chain_id") == "1151111081099710" else token.get("chain_id") or token.get("chainId"),
            "name": token.get("name"),
            "logoUrl": token.get("logoURI",""),
            "symbol": token.get("symbol"),
            "address": token.get("contract_address") or token.get("address"),
            "decimals": token.get("decimals", 6),  # Default to 6 if not provided
            "isEnabled": True
        }
        for token in tokens
    ]

    # Prepare payload
    api_url = f"{ACME_URL}/telegram/currency/create-or-update-for-dex-aggregator"
    headers = {"X-API-KEY": ACME_API_KEY, "Content-Type": "application/json"}
    payload = {"dexAggregatorId": dex_aggregator_id, "currencies": sanitized_tokens}

    # Attempt API registration with retries
    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                logger.debug(f"Attempt {attempt + 1}: Registering tokens on Acme at {api_url} {headers} {payload}")
                async with session.post(api_url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info("Tokens registered successfully.")
                        # Return the first object from 'currenciesLoaded' if it exists, otherwise None
                        return data.get('data', {}).get('currenciesLoaded', [None])[0]
                    else:
                        logger.error(f"Attempt {attempt + 1}: Registration failed with status {response.status}")
                        response.raise_for_status()

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: Client error occurred: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")

    raise ValueError("Failed to register tokens after multiple attempts.")
