def get_token(ticker: str, type: str):
  # Mapping of tickers to chainId and token_address for trading
  TRADE_TOKENS = {
      "BRETT": {"chainId": "8453", "tokenAddress": "0x532f27101965dd16442e59d40670faf5ebb142e4"},
      "PONKE": {"chainId": "solana", "tokenAddress": "5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK8PSWmrRC"},
      # Add more trade tokens as needed
  }

  # Mapping of tickers to chainId and token_address for payments
  PAY_TOKENS = {
      "USDC": {"chainId": "42161", "tokenAddress": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals":6},
      # Add more pay tokens as needed
  }

  """Retrieve token data from the appropriate mapping based on type."""
  if type == "trade":
      token_data = TRADE_TOKENS.get(ticker.upper())
  elif type == "pay":
      token_data = PAY_TOKENS.get(ticker.upper())
  else:
      return {"error": "Invalid type. Must be 'trade' or 'pay'."}

  if token_data:
      return token_data
  else:
      return {"error": "Ticker not found."}