import aiohttp
from config import logger, SUPPORTED_CHAIN_IDS

async def fetch_and_format_token_market_data(contract_address: str, chain_id: str, decimals: str) -> dict:
    """
    Fetches and formats token data from CoinGecko API based on the token symbol and chain ID.

    Args:
        contract_address (str): The address of the token contract.
        chain_id (str): The chain ID.

    Returns:
        dict: Formatted token data including change_24h, mcap, volume_24h, circulating_supply, and total_supply.
    """
    # Get the platform ID from the supported chain IDs, default to 'solana' if not found
    logger.debug(f"Chain ID {chain_id} for Coingecko: {SUPPORTED_CHAIN_IDS.get(str(chain_id))}")

    platform_id = SUPPORTED_CHAIN_IDS.get(str(chain_id), 'solana')

    # Build the CoinGecko API URL
    url = (
        f"https://api.coingecko.com/api/v3/simple/token_price/{platform_id}"
        f"?contract_addresses={contract_address}"
        "&vs_currencies=usd&include_market_cap=true&"
        "include_24hr_vol=true&include_24hr_change=true&"
        "include_last_updated_at=true"
    )

    logger.info(f"Fetching token market data for {contract_address} on chain {chain_id}.")
    logger.debug(f"CoinGecko API URL: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            # Make the GET request to fetch token data
            async with session.get(url) as response:
                response.raise_for_status()  # Raise an error for bad responses
                data = await response.json()  # Await the JSON response

                logger.debug(f"Response data from CoinGecko: {data}")

                if not data:
                    logger.warning(f"No data found for token address: {contract_address}")
                    return {}

                # Extract the contract address from the keys (assuming you want the first one)
                contract_address = list(data.keys())[0]
                data = data[contract_address]  # Access the data for that specific contract

                # Extract and format financial metrics
                formatted_data = {
                    "price": format_financial_metrics(data.get("usd"), "price"),
                    "change_24h": format_financial_metrics(data.get("usd_24h_change"), "change_24h"),
                    "mcap": format_financial_metrics(data.get("usd_market_cap"), "mcap"),
                    "volume_24h": format_financial_metrics(data.get("usd_24h_vol"), "volume"),
                    # "circulating_supply": format_financial_metrics(data.get("circulating_supply"), "circulating_supply"),
                    # "total_supply": format_financial_metrics(data.get("total_supply"), "total_supply")
                }

                logger.info(f"Successfully fetched and formatted data for {contract_address}: {formatted_data}")
                return formatted_data

    except aiohttp.ClientError as e:
        logger.error(f"Failed to fetch token data from CoinGecko: {str(e)}")
        return {}  # Return empty dict in case of error

def format_financial_metrics(value: float, metric_type: str) -> str:
    """Format financial metrics for display."""

    if value is None:
        return "N/A"

    if metric_type == "price":
        if value < 0.001:  # Start using scientific notation for values less than 0.001
            formatted = f"${value:.2e}"  # Format in scientific notation
            base, exp = formatted.split('e')
            return f"{base}e{int(exp)}"  # Compress the exponent
        return f"${value:.4f}".rstrip('0').rstrip('.')  # Standard decimal format for values >= 0.001

    if metric_type in {"mcap", "volume", "circulating_supply", "total_supply"}:
        suffixes = ["", "K", "M", "B", "T"]
        idx = 0
        while value >= 1000 and idx < len(suffixes) - 1:
            value /= 1000
            idx += 1
        return f"{value:.2f}{suffixes[idx]}"  # Add appropriate suffix

    if metric_type == "change_24h":
        sign = "+" if value > 0 else ""
        emoji = "🟢" if value > 0 else "🔴"
        return f" {sign}{value:.2f}% {emoji}"

    return "N/A"
