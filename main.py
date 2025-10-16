import asyncio
import hashlib
import hmac
import httpx
import os
from fastmcp import FastMCP
from datetime import datetime
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from urllib.parse import urlencode

# Load environment variables
load_dotenv()

# Initialize the MCP server
mcp = FastMCP("Binance Trading Assistant")

# Binance API Configuration
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")
BINANCE_ENV = os.getenv("BINANCE_ENVIRONMENT", "production")

# API Base URLs
if BINANCE_ENV == "testnet":
    BASE_URL = "https://testnet.binance.vision"
else:
    BASE_URL = "https://api.binance.com"

ANNOUNCEMENT_URL = "https://www.binance.com/bapi/composite/v1/public/market/notice/get"


class BinanceAPI:
    """Helper class for Binance API interactions"""
    
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for authenticated requests"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Dict[str, Any]:
        """Make an authenticated request to Binance API"""
        if params is None:
            params = {}
        
        headers = {"X-MBX-APIKEY": self.api_key} if self.api_key else {}
        
        if signed:
            params['timestamp'] = int(datetime.now().timestamp() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._generate_signature(query_string)
        
        url = f"{self.base_url}{endpoint}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method.upper() == "GET":
                response = await client.get(url, params=params, headers=headers)
            elif method.upper() == "POST":
                response = await client.post(url, params=params, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()


# Initialize API client
api_client = BinanceAPI(BINANCE_API_KEY, BINANCE_API_SECRET, BASE_URL)


# ==================== PUBLIC/ANNOUNCEMENT TOOLS ====================

@mcp.tool()
async def fetch_latest_announcements(count: int = 20, page: int = 1) -> str:
    """
    Fetch the latest Binance announcements in Markdown format.
    
    Args:
        count: Number of announcements to fetch (max 20)
        page: Page number to fetch (default 1)
    
    Returns:
        Markdown formatted string with announcement titles, URLs, and timestamps
    """
    if count > 20:
        count = 20
    if page < 1:
        page = 1

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(ANNOUNCEMENT_URL, params={"page": page, "rows": count})
            response.raise_for_status()
            data = response.json()
            
            if data["code"] != "000000":
                return f"❌ API error: {data.get('message', 'Unknown error')}"
            
            announcements = data["data"]
            markdown = "# 📢 Binance Announcements\n\n"
            
            for ann in announcements:
                title = ann.get("title", "No Title")
                url = ann.get("url", "No URL")
                time = datetime.fromtimestamp(ann.get("time", 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                markdown += f"- [{title}]({url}) _({time})_\n"
            
            return markdown if announcements else "# No Announcements Found\n"
        except Exception as e:
            return f"❌ Failed to fetch announcements: {str(e)}"


@mcp.tool()
async def get_ticker_price(symbol: Optional[str] = None) -> str:
    """
    Get current price ticker for a symbol or all symbols.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT'). If None, returns all symbols
    
    Returns:
        Markdown formatted price information
    """
    try:
        endpoint = "/api/v3/ticker/price"
        params = {"symbol": symbol.upper()} if symbol else {}
        
        data = await api_client._request("GET", endpoint, params, signed=False)
        
        if isinstance(data, list):
            # Multiple symbols
            markdown = "# 💰 Price Tickers (Top 20)\n\n"
            markdown += "| Symbol | Price |\n"
            markdown += "|--------|-------|\n"
            for item in data[:20]:
                markdown += f"| {item['symbol']} | ${float(item['price']):.8f} |\n"
            if len(data) > 20:
                markdown += f"\n_Showing 20 of {len(data)} symbols. Specify a symbol for detailed info._\n"
        else:
            # Single symbol
            markdown = f"# 💰 {data['symbol']} Price\n\n"
            markdown += f"**Current Price:** ${float(data['price']):.8f}\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch ticker price: {str(e)}"


@mcp.tool()
async def get_24hr_ticker(symbol: str) -> str:
    """
    Get 24-hour price change statistics for a symbol.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
    
    Returns:
        Markdown formatted 24hr statistics
    """
    try:
        endpoint = "/api/v3/ticker/24hr"
        params = {"symbol": symbol.upper()}
        
        data = await api_client._request("GET", endpoint, params, signed=False)
        
        markdown = f"# 📊 24hr Statistics for {data['symbol']}\n\n"
        markdown += f"**Price Change:** ${float(data['priceChange']):.8f} ({float(data['priceChangePercent']):.2f}%)\n"
        markdown += f"**High Price:** ${float(data['highPrice']):.8f}\n"
        markdown += f"**Low Price:** ${float(data['lowPrice']):.8f}\n"
        markdown += f"**Current Price:** ${float(data['lastPrice']):.8f}\n"
        markdown += f"**Volume:** {float(data['volume']):.2f} {symbol[:3]}\n"
        markdown += f"**Quote Volume:** ${float(data['quoteVolume']):.2f}\n"
        markdown += f"**Number of Trades:** {data['count']}\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch 24hr ticker: {str(e)}"


# ==================== SPOT ACCOUNT TOOLS ====================

@mcp.tool()
async def get_account_info() -> str:
    """
    Get current spot account information including balances and permissions.
    
    Returns:
        Markdown formatted account information
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/api/v3/account"
        data = await api_client._request("GET", endpoint, signed=True)
        
        markdown = "# 👤 Spot Account Information\n\n"
        markdown += f"**Maker Commission:** {data['makerCommission']} bps\n"
        markdown += f"**Taker Commission:** {data['takerCommission']} bps\n"
        markdown += f"**Can Trade:** {'✅' if data['canTrade'] else '❌'}\n"
        markdown += f"**Can Withdraw:** {'✅' if data['canWithdraw'] else '❌'}\n"
        markdown += f"**Can Deposit:** {'✅' if data['canDeposit'] else '❌'}\n\n"
        
        # Filter non-zero balances
        balances = [b for b in data['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]
        
        if balances:
            markdown += "## 💼 Non-Zero Balances\n\n"
            markdown += "| Asset | Free | Locked | Total |\n"
            markdown += "|-------|------|--------|-------|\n"
            
            for balance in balances:
                free = float(balance['free'])
                locked = float(balance['locked'])
                total = free + locked
                markdown += f"| {balance['asset']} | {free:.8f} | {locked:.8f} | {total:.8f} |\n"
        else:
            markdown += "## 💼 No balances found\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch account info: {str(e)}"


@mcp.tool()
async def get_spot_open_orders(symbol: Optional[str] = None) -> str:
    """
    Get all open spot orders for a symbol or all symbols.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT'). If None, returns all open orders
    
    Returns:
        Markdown formatted list of open orders
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/api/v3/openOrders"
        params = {"symbol": symbol.upper()} if symbol else {}
        
        orders = await api_client._request("GET", endpoint, params, signed=True)
        
        if not orders:
            return f"# 📋 No Open Orders{' for ' + symbol if symbol else ''}\n"
        
        markdown = f"# 📋 Open Spot Orders{' for ' + symbol if symbol else ''}\n\n"
        markdown += f"**Total Open Orders:** {len(orders)}\n\n"
        
        for order in orders:
            markdown += f"### Order #{order['orderId']}\n"
            markdown += f"- **Symbol:** {order['symbol']}\n"
            markdown += f"- **Side:** {order['side']}\n"
            markdown += f"- **Type:** {order['type']}\n"
            markdown += f"- **Price:** ${float(order['price']):.8f}\n"
            markdown += f"- **Original Qty:** {float(order['origQty']):.8f}\n"
            markdown += f"- **Executed Qty:** {float(order['executedQty']):.8f}\n"
            markdown += f"- **Status:** {order['status']}\n"
            markdown += f"- **Time:** {datetime.fromtimestamp(order['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch open orders: {str(e)}"


@mcp.tool()
async def get_spot_trade_history(symbol: str, limit: int = 10) -> str:
    """
    Get recent spot trade history for a symbol.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT')
        limit: Number of trades to fetch (default 10, max 1000)
    
    Returns:
        Markdown formatted trade history
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/api/v3/myTrades"
        params = {"symbol": symbol.upper(), "limit": min(limit, 1000)}
        
        trades = await api_client._request("GET", endpoint, params, signed=True)
        
        if not trades:
            return f"# 📜 No Trade History for {symbol}\n"
        
        markdown = f"# 📜 Trade History for {symbol}\n\n"
        markdown += f"**Total Trades:** {len(trades)}\n\n"
        markdown += "| Time | Side | Price | Quantity | Commission | Total |\n"
        markdown += "|------|------|-------|----------|------------|-------|\n"
        
        for trade in trades:
            time = datetime.fromtimestamp(trade['time'] / 1000).strftime('%m-%d %H:%M')
            side = "🟢 BUY" if trade['isBuyer'] else "🔴 SELL"
            price = float(trade['price'])
            qty = float(trade['qty'])
            commission = f"{float(trade['commission']):.8f} {trade['commissionAsset']}"
            total = price * qty
            markdown += f"| {time} | {side} | ${price:.8f} | {qty:.8f} | {commission} | ${total:.2f} |\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch trade history: {str(e)}"


# ==================== FUTURES ACCOUNT TOOLS ====================

@mcp.tool()
async def get_futures_account_balance() -> str:
    """
    Get USDT-M Futures account balance and positions.
    
    Returns:
        Markdown formatted futures account information
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        # Get account info
        endpoint = "/fapi/v2/account"
        data = await api_client._request("GET", endpoint, signed=True)
        
        markdown = "# 🎯 USDT-M Futures Account\n\n"
        markdown += f"**Total Wallet Balance:** ${float(data['totalWalletBalance']):.2f}\n"
        markdown += f"**Total Unrealized Profit:** ${float(data['totalUnrealizedProfit']):.2f}\n"
        markdown += f"**Total Margin Balance:** ${float(data['totalMarginBalance']):.2f}\n"
        markdown += f"**Available Balance:** ${float(data['availableBalance']):.2f}\n"
        markdown += f"**Max Withdraw Amount:** ${float(data['maxWithdrawAmount']):.2f}\n\n"
        
        # Assets with balance
        assets = [a for a in data['assets'] if float(a['walletBalance']) > 0]
        if assets:
            markdown += "## 💼 Asset Balances\n\n"
            markdown += "| Asset | Wallet Balance | Unrealized Profit | Margin Balance |\n"
            markdown += "|-------|----------------|-------------------|----------------|\n"
            
            for asset in assets:
                markdown += f"| {asset['asset']} | {float(asset['walletBalance']):.2f} | {float(asset['unrealizedProfit']):.2f} | {float(asset['marginBalance']):.2f} |\n"
            markdown += "\n"
        
        # Active positions
        positions = [p for p in data['positions'] if float(p['positionAmt']) != 0]
        if positions:
            markdown += "## 📊 Active Positions\n\n"
            
            for pos in positions:
                side = "🟢 LONG" if float(pos['positionAmt']) > 0 else "🔴 SHORT"
                markdown += f"### {pos['symbol']} ({side})\n"
                markdown += f"- **Position Amount:** {float(pos['positionAmt']):.8f}\n"
                markdown += f"- **Entry Price:** ${float(pos['entryPrice']):.8f}\n"
                markdown += f"- **Unrealized Profit:** ${float(pos['unrealizedProfit']):.2f}\n"
                markdown += f"- **Leverage:** {pos['leverage']}x\n"
                markdown += f"- **Isolated:** {'✅' if pos['isolated'] else '❌'}\n\n"
        else:
            markdown += "## 📊 No Active Positions\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch futures account: {str(e)}"


@mcp.tool()
async def get_futures_open_orders(symbol: Optional[str] = None) -> str:
    """
    Get all open futures orders for a symbol or all symbols.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT'). If None, returns all open orders
    
    Returns:
        Markdown formatted list of open futures orders
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/fapi/v1/openOrders"
        params = {"symbol": symbol.upper()} if symbol else {}
        
        orders = await api_client._request("GET", endpoint, params, signed=True)
        
        if not orders:
            return f"# 📋 No Open Futures Orders{' for ' + symbol if symbol else ''}\n"
        
        markdown = f"# 📋 Open Futures Orders{' for ' + symbol if symbol else ''}\n\n"
        markdown += f"**Total Open Orders:** {len(orders)}\n\n"
        
        for order in orders:
            markdown += f"### Order #{order['orderId']}\n"
            markdown += f"- **Symbol:** {order['symbol']}\n"
            markdown += f"- **Side:** {order['side']}\n"
            markdown += f"- **Type:** {order['type']}\n"
            markdown += f"- **Price:** ${float(order['price']):.8f}\n"
            markdown += f"- **Original Qty:** {float(order['origQty']):.8f}\n"
            markdown += f"- **Executed Qty:** {float(order['executedQty']):.8f}\n"
            markdown += f"- **Status:** {order['status']}\n"
            markdown += f"- **Reduce Only:** {'✅' if order['reduceOnly'] else '❌'}\n"
            markdown += f"- **Time:** {datetime.fromtimestamp(order['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch futures open orders: {str(e)}"


@mcp.tool()
async def get_futures_income_history(symbol: Optional[str] = None, income_type: Optional[str] = None, limit: int = 20) -> str:
    """
    Get futures income history (realized PnL, funding fees, commissions, etc.).
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT'). If None, returns all symbols
        income_type: Type of income (TRANSFER, WELCOME_BONUS, REALIZED_PNL, FUNDING_FEE, COMMISSION, etc.)
        limit: Number of records to fetch (default 20, max 1000)
    
    Returns:
        Markdown formatted income history
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/fapi/v1/income"
        params = {"limit": min(limit, 1000)}
        if symbol:
            params["symbol"] = symbol.upper()
        if income_type:
            params["incomeType"] = income_type.upper()
        
        incomes = await api_client._request("GET", endpoint, params, signed=True)
        
        if not incomes:
            return f"# 💸 No Income History Found\n"
        
        markdown = f"# 💸 Futures Income History\n\n"
        markdown += f"**Total Records:** {len(incomes)}\n\n"
        markdown += "| Time | Symbol | Type | Income | Asset |\n"
        markdown += "|------|--------|------|--------|-------|\n"
        
        total_income = {}
        for income in incomes:
            time = datetime.fromtimestamp(income['time'] / 1000).strftime('%m-%d %H:%M')
            income_amount = float(income['income'])
            asset = income['asset']
            
            # Track totals
            if asset not in total_income:
                total_income[asset] = 0
            total_income[asset] += income_amount
            
            markdown += f"| {time} | {income['symbol']} | {income['incomeType']} | {income_amount:.8f} | {asset} |\n"
        
        markdown += "\n## 📈 Total Income by Asset\n\n"
        for asset, total in total_income.items():
            markdown += f"- **{asset}:** {total:.8f}\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch income history: {str(e)}"


# ==================== MARGIN ACCOUNT TOOLS ====================

@mcp.tool()
async def get_margin_account() -> str:
    """
    Get cross margin account details including balances and margin level.
    
    Returns:
        Markdown formatted margin account information
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/sapi/v1/margin/account"
        data = await api_client._request("GET", endpoint, signed=True)
        
        markdown = "# 🔄 Cross Margin Account\n\n"
        markdown += f"**Margin Level:** {float(data['marginLevel']):.4f}\n"
        markdown += f"**Total Asset (BTC):** {float(data['totalAssetOfBtc']):.8f}\n"
        markdown += f"**Total Liability (BTC):** {float(data['totalLiabilityOfBtc']):.8f}\n"
        markdown += f"**Total Net Asset (BTC):** {float(data['totalNetAssetOfBtc']):.8f}\n"
        markdown += f"**Can Trade:** {'✅' if data['tradeEnabled'] else '❌'}\n"
        markdown += f"**Can Transfer:** {'✅' if data['transferEnabled'] else '❌'}\n"
        markdown += f"**Can Borrow:** {'✅' if data['borrowEnabled'] else '❌'}\n\n"
        
        # Assets with balance or borrowed
        assets = [a for a in data['userAssets'] if float(a['netAsset']) != 0 or float(a['borrowed']) > 0]
        
        if assets:
            markdown += "## 💼 Asset Details\n\n"
            markdown += "| Asset | Free | Locked | Borrowed | Interest | Net Asset |\n"
            markdown += "|-------|------|--------|----------|----------|----------|\n"
            
            for asset in assets:
                markdown += f"| {asset['asset']} | {float(asset['free']):.8f} | {float(asset['locked']):.8f} | {float(asset['borrowed']):.8f} | {float(asset['interest']):.8f} | {float(asset['netAsset']):.8f} |\n"
        else:
            markdown += "## 💼 No margin assets found\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch margin account: {str(e)}"


@mcp.tool()
async def get_isolated_margin_account(symbol: Optional[str] = None) -> str:
    """
    Get isolated margin account details for all symbols or a specific symbol.
    
    Args:
        symbol: Trading pair symbol (e.g., 'BTCUSDT'). If None, returns all isolated margin accounts
    
    Returns:
        Markdown formatted isolated margin account information
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/sapi/v1/margin/isolated/account"
        params = {"symbols": symbol.upper()} if symbol else {}
        
        data = await api_client._request("GET", endpoint, params, signed=True)
        
        assets = data.get('assets', [])
        
        if not assets:
            return f"# 🔄 No Isolated Margin Accounts Found\n"
        
        markdown = f"# 🔄 Isolated Margin Accounts\n\n"
        markdown += f"**Total Accounts:** {len(assets)}\n"
        markdown += f"**Total Net Asset (BTC):** {float(data.get('totalNetAssetOfBtc', 0)):.8f}\n\n"
        
        for asset in assets:
            markdown += f"## {asset['symbol']}\n\n"
            markdown += f"**Margin Level:** {float(asset['marginLevel']):.4f}\n"
            markdown += f"**Margin Ratio:** {float(asset['marginRatio']):.4f}\n"
            markdown += f"**Liquidate Price:** ${float(asset['liquidatePrice']):.8f}\n"
            markdown += f"**Can Trade:** {'✅' if asset['tradeEnabled'] else '❌'}\n\n"
            
            markdown += "### Base Asset\n"
            base = asset['baseAsset']
            markdown += f"- **Asset:** {base['asset']}\n"
            markdown += f"- **Free:** {float(base['free']):.8f}\n"
            markdown += f"- **Borrowed:** {float(base['borrowed']):.8f}\n"
            markdown += f"- **Interest:** {float(base['interest']):.8f}\n"
            markdown += f"- **Net Asset:** {float(base['netAsset']):.8f}\n\n"
            
            markdown += "### Quote Asset\n"
            quote = asset['quoteAsset']
            markdown += f"- **Asset:** {quote['asset']}\n"
            markdown += f"- **Free:** {float(quote['free']):.8f}\n"
            markdown += f"- **Borrowed:** {float(quote['borrowed']):.8f}\n"
            markdown += f"- **Interest:** {float(quote['interest']):.8f}\n"
            markdown += f"- **Net Asset:** {float(quote['netAsset']):.8f}\n\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch isolated margin account: {str(e)}"


# ==================== ASSET INFORMATION TOOLS ====================

@mcp.tool()
async def get_asset_distribution() -> str:
    """
    Get a portfolio distribution snapshot showing asset allocation across spot, futures, and margin accounts.
    
    Returns:
        Markdown formatted portfolio distribution
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    markdown = "# 🎯 Portfolio Distribution Snapshot\n\n"
    
    try:
        # Get spot account
        spot_data = await api_client._request("GET", "/api/v3/account", signed=True)
        spot_balances = {b['asset']: float(b['free']) + float(b['locked']) 
                        for b in spot_data['balances'] if float(b['free']) > 0 or float(b['locked']) > 0}
        
        markdown += "## 💼 Spot Account\n\n"
        if spot_balances:
            for asset, balance in sorted(spot_balances.items(), key=lambda x: x[1], reverse=True):
                markdown += f"- **{asset}:** {balance:.8f}\n"
        else:
            markdown += "_No spot balances_\n"
        markdown += "\n"
    except Exception as e:
        markdown += f"## 💼 Spot Account\n\n❌ Error: {str(e)}\n\n"
    
    try:
        # Get futures account
        futures_data = await api_client._request("GET", "/fapi/v2/account", signed=True)
        futures_balance = float(futures_data['totalWalletBalance'])
        
        markdown += "## 🎯 USDT-M Futures\n\n"
        markdown += f"- **Total Wallet Balance:** ${futures_balance:.2f}\n"
        markdown += f"- **Unrealized Profit:** ${float(futures_data['totalUnrealizedProfit']):.2f}\n"
        
        positions = [p for p in futures_data['positions'] if float(p['positionAmt']) != 0]
        if positions:
            markdown += f"- **Active Positions:** {len(positions)}\n"
        markdown += "\n"
    except Exception as e:
        markdown += f"## 🎯 USDT-M Futures\n\n❌ Error: {str(e)}\n\n"
    
    try:
        # Get margin account
        margin_data = await api_client._request("GET", "/sapi/v1/margin/account", signed=True)
        
        markdown += "## 🔄 Cross Margin\n\n"
        markdown += f"- **Total Net Asset (BTC):** {float(margin_data['totalNetAssetOfBtc']):.8f}\n"
        markdown += f"- **Margin Level:** {float(margin_data['marginLevel']):.4f}\n\n"
    except Exception as e:
        markdown += f"## 🔄 Cross Margin\n\n❌ Error: {str(e)}\n\n"
    
    return markdown


@mcp.tool()
async def get_deposit_address(coin: str, network: Optional[str] = None) -> str:
    """
    Get deposit address for a specific coin and network.
    
    Args:
        coin: Coin name (e.g., 'BTC', 'ETH', 'USDT')
        network: Network name (e.g., 'BTC', 'ETH', 'TRX'). If None, returns all networks
    
    Returns:
        Markdown formatted deposit address information
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/sapi/v1/capital/deposit/address"
        params = {"coin": coin.upper()}
        if network:
            params["network"] = network.upper()
        
        data = await api_client._request("GET", endpoint, params, signed=True)
        
        markdown = f"# 📥 Deposit Address for {coin.upper()}\n\n"
        
        if isinstance(data, list):
            for addr in data:
                markdown += f"## Network: {addr.get('network', 'Unknown')}\n"
                markdown += f"- **Address:** `{addr['address']}`\n"
                if addr.get('tag'):
                    markdown += f"- **Tag/Memo:** `{addr['tag']}`\n"
                markdown += "\n"
        else:
            markdown += f"**Network:** {data.get('network', 'Unknown')}\n"
            markdown += f"**Address:** `{data['address']}`\n"
            if data.get('tag'):
                markdown += f"**Tag/Memo:** `{data['tag']}`\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch deposit address: {str(e)}"


@mcp.tool()
async def get_deposit_history(coin: Optional[str] = None, status: Optional[int] = None, limit: int = 10) -> str:
    """
    Get deposit history for all coins or a specific coin.
    
    Args:
        coin: Coin name (e.g., 'BTC', 'ETH'). If None, returns all coins
        status: 0=pending, 1=success, 6=credited but cannot withdraw. If None, returns all statuses
        limit: Number of records to fetch (default 10, max 1000)
    
    Returns:
        Markdown formatted deposit history
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/sapi/v1/capital/deposit/hisrec"
        params = {"limit": min(limit, 1000)}
        if coin:
            params["coin"] = coin.upper()
        if status is not None:
            params["status"] = status
        
        deposits = await api_client._request("GET", endpoint, params, signed=True)
        
        if not deposits:
            return f"# 📥 No Deposit History Found\n"
        
        markdown = f"# 📥 Deposit History\n\n"
        markdown += f"**Total Records:** {len(deposits)}\n\n"
        markdown += "| Time | Coin | Amount | Network | Status |\n"
        markdown += "|------|------|--------|---------|--------|\n"
        
        status_map = {0: "⏳ Pending", 1: "✅ Success", 6: "⚠️ Credited"}
        
        for deposit in deposits:
            time = datetime.fromtimestamp(deposit['insertTime'] / 1000).strftime('%m-%d %H:%M')
            status_text = status_map.get(deposit['status'], f"Status {deposit['status']}")
            markdown += f"| {time} | {deposit['coin']} | {float(deposit['amount']):.8f} | {deposit.get('network', 'N/A')} | {status_text} |\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch deposit history: {str(e)}"


@mcp.tool()
async def get_withdraw_history(coin: Optional[str] = None, status: Optional[int] = None, limit: int = 10) -> str:
    """
    Get withdrawal history for all coins or a specific coin.
    
    Args:
        coin: Coin name (e.g., 'BTC', 'ETH'). If None, returns all coins
        status: 0=email sent, 1=cancelled, 2=awaiting approval, 3=rejected, 4=processing, 5=failure, 6=completed
        limit: Number of records to fetch (default 10, max 1000)
    
    Returns:
        Markdown formatted withdrawal history
    """
    if not BINANCE_API_KEY or not BINANCE_API_SECRET:
        return "❌ API keys not configured. Please set BINANCE_API_KEY and BINANCE_API_SECRET in .env file"
    
    try:
        endpoint = "/sapi/v1/capital/withdraw/history"
        params = {"limit": min(limit, 1000)}
        if coin:
            params["coin"] = coin.upper()
        if status is not None:
            params["status"] = status
        
        withdrawals = await api_client._request("GET", endpoint, params, signed=True)
        
        if not withdrawals:
            return f"# 📤 No Withdrawal History Found\n"
        
        markdown = f"# 📤 Withdrawal History\n\n"
        markdown += f"**Total Records:** {len(withdrawals)}\n\n"
        markdown += "| Time | Coin | Amount | Network | Fee | Status |\n"
        markdown += "|------|------|--------|---------|-----|--------|\n"
        
        status_map = {
            0: "📧 Email Sent",
            1: "❌ Cancelled",
            2: "⏳ Awaiting Approval",
            3: "🚫 Rejected",
            4: "⚙️ Processing",
            5: "❌ Failure",
            6: "✅ Completed"
        }
        
        for withdrawal in withdrawals:
            time = datetime.fromtimestamp(withdrawal['applyTime'] / 1000).strftime('%m-%d %H:%M')
            status_text = status_map.get(withdrawal['status'], f"Status {withdrawal['status']}")
            markdown += f"| {time} | {withdrawal['coin']} | {float(withdrawal['amount']):.8f} | {withdrawal.get('network', 'N/A')} | {float(withdrawal.get('transactionFee', 0)):.8f} | {status_text} |\n"
        
        return markdown
    except Exception as e:
        return f"❌ Failed to fetch withdrawal history: {str(e)}"


if __name__ == "__main__":
    mcp.run()
