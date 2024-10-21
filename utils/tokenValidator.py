from config import logger, SUPPORTED_CHAIN_IDS, LIFI_API_URL, ACME_APP_URL
from utils.createTradingLink import create_trading_link
import aiohttp
from telegram import Update
from telegram.ext import ContextTypes
import re

# Regex pattern to detect if the token is an EVM contract address (42 hex characters)
EVM_CONTRACT_ADDRESS_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")

# Regex pattern for detecting Solana Virtual Machine (SVM) contract addresses (Base58, typically 32 bytes)
SVM_CONTRACT_ADDRESS_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

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
                token_address = token_data.get("contract_address")
                intent_id = await get_intent_id_from_auth(context, token_address)
                trading_link = await generate_trading_link(context, token_data, intent_id)
                if trading_link:
                    token_data["tradingLink"] = trading_link
                    valid_tokens.append(token_data)
                    logger.info(f"Valid token found: {token_data['symbol']} ({token_data['contract_address']})")
                else:
                    logger.error(f"Failed to generate trading link for token: {token}")
                    invalid_tokens.append(token)
            else:
                logger.warning(f"Invalid or missing token data for: {token}")
                invalid_tokens.append(token)

        elif isinstance(token, dict):
            #logger.debug(f"Processing token object: {token}")
            intent_id = token.get("intentId")
            chain_id = token.get("chainId")
            token_address = token.get("tokenAddress")

            token_data = await fetch_token_data_from_chains(token=token_address, chain_id=chain_id)

            if token_data and "error" not in token_data:
                trading_link = await generate_trading_link(context, token_data, intent_id)

                if trading_link:
                    token_data["tradingLink"] = trading_link
                    valid_tokens.append(token_data)
                    logger.info(f"Valid token object: {token_data['symbol']} ({token_address})")
                else:
                    logger.error(f"Failed to create trading link for token object.")
                    invalid_tokens.append(token)
            else:
                logger.warning(f"Invalid token object: {token}")
                invalid_tokens.append(token)
        else:
            logger.warning(f"Unsupported token format: {token}")
            invalid_tokens.append(token)

    logger.info(f"Validation completed. Valid tokens: {len(valid_tokens)}, Invalid tokens: {len(invalid_tokens)}")
    return valid_tokens, invalid_tokens

async def generate_trading_link(context: ContextTypes.DEFAULT_TYPE, token_data, intent_id):
    """Generate a trading link using an existing or newly created intent ID."""
    logger.debug(f"Generating trading link for token: {token_data['symbol']}")
    if intent_id:
        trading_link = f"{ACME_APP_URL}/buy/{intent_id}"
        logger.debug(f"Using existing intent ID for trading link: {trading_link}")
    else:
        chain_id = token_data.get("chain_id")
        token_address = token_data.get("contract_address")
        trading_link = await create_trading_link(context, chain_id, token_address, "")

        if trading_link:
            logger.debug(f"Successfully created trading link: {trading_link}")
        else:
            logger.error(f"Failed to create trading link for token: {token_data}")

    return trading_link

async def get_intent_id_from_auth(context: ContextTypes.DEFAULT_TYPE, token_address: str):
    """Retrieve intent ID from the user's auth result if available."""
    logger.debug(f"Fetching intent ID for token: {token_address}")
    auth_result = context.user_data.get("auth_result", {})
    token_info_list = auth_result.get("tokens", [])

    for token_info in token_info_list:
        if token_info.get("tokenAddress") == token_address:
            intent_id = token_info.get("intentId")
            logger.debug(f"Found intent ID: {intent_id}")
            return intent_id
    logger.warning(f"No intent ID found for token: {token_address}")
    return None

async def fetch_token_data_from_chains(token: str, chain_id: str | None = None):
    """Fetch token data from the LiFi API."""
    logger.info(f"Fetching token data for: {token}, Chain ID: {chain_id}")
    url = f"{LIFI_API_URL}/token"
    chain_id = '1151111081099710' if chain_id == 'solana' else chain_id
    chains = [(chain_id, SUPPORTED_CHAIN_IDS.get(chain_id))] if chain_id else SUPPORTED_CHAIN_IDS.items()

    async with aiohttp.ClientSession() as session:
        for current_chain_id, platform_name in chains:
            if not platform_name:
                logger.error(f"Unsupported chain ID: {current_chain_id}")
                return {"error": f"Chain ID '{current_chain_id}' is not supported."}

            params = {"chain": current_chain_id, "token": token}
            logger.debug(f"Fetching token data with params: {params}")

            try:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to fetch token data. Status: {response.status}")
                        continue

                    token_data = await response.json()
                    #logger.debug(f"Fetched token data: {token_data}")
                    return extract_token_data(token_data)
            except aiohttp.ClientError as e:
                logger.exception(f"Network error: {e}")
                continue

    logger.warning("Token not found or invalid price across all chains.")
    return {"error": "Token not found or price is invalid."}

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