# 🚀 Binance MCP Server

A comprehensive Model Context Protocol (MCP) server for Binance, providing read-only access to your trading accounts, portfolio data, market information, and more through AI assistants like Claude.

## ✨ Features

This MCP server provides **20+ read-only tools** across multiple categories:

### 📢 Public Market Data
- `fetch_latest_announcements` - Get latest Binance announcements
- `get_ticker_price` - Current price for any symbol or all symbols
- `get_24hr_ticker` - 24-hour statistics (price change, volume, high/low)

### 💼 Spot Account
- `get_account_info` - Account balances, permissions, and commission rates
- `get_spot_open_orders` - All open spot orders
- `get_spot_trade_history` - Recent trade history for any symbol

### 🎯 USDT-M Futures
- `get_futures_account_balance` - Futures wallet balance and active positions
- `get_futures_open_orders` - All open futures orders
- `get_futures_income_history` - Realized PnL, funding fees, commissions

### 🔄 Margin Trading
- `get_margin_account` - Cross margin account details and balances
- `get_isolated_margin_account` - Isolated margin positions and margin levels

### 📊 Portfolio Overview
- `get_asset_distribution` - Complete portfolio snapshot across all accounts

### 💰 Deposits & Withdrawals
- `get_deposit_address` - Get deposit addresses for any coin/network
- `get_deposit_history` - View deposit transaction history
- `get_withdraw_history` - View withdrawal transaction history

## ⚡ Quick Start

```bash
# 1. Clone and install
git clone <your-repo-url>
cd binance-mcp
uv sync

# 2. Configure API keys
cp .env.example .env
# Edit .env with your Binance API keys

# 3. Test it locally with inspector UI
uv run fastmcp dev main.py

# 4. Add to Claude Desktop config (see Integration section below)
```

## 🔧 Installation

### Prerequisites
- Python 3.11 or higher
- A Binance account with API access
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Step 1: Clone and Install Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd binance-mcp

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

### Step 2: Create Binance API Keys

1. Log in to [Binance](https://www.binance.com)
2. Go to **Profile → API Management**
3. Create a new API key
4. **Important:** Only enable "Enable Reading" permission (read-only)
5. Save your API Key and Secret Key securely

### Step 3: Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API credentials:

```env
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here
BINANCE_ENVIRONMENT=production
```

> **Note:** Never commit your `.env` file to version control. It's already in `.gitignore`.

## 🎯 Usage

### Running Locally

#### Method 1: Using FastMCP (Recommended)

```bash
# Development mode with auto-reload and inspector UI
uv run fastmcp dev main.py

# Production mode
uv run fastmcp run main.py
```

**Development mode** provides:
- 🔄 Auto-reload on file changes
- 🌐 Web inspector UI at http://localhost:5173
- 📊 Real-time tool testing and debugging

#### Method 2: Using Python Directly

```bash
# Activate virtual environment (if using uv)
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Run the MCP server
python main.py
```

### Integrating with Claude Desktop

Add this to your Claude Desktop configuration file:

**On macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`  
**On Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

#### Method 1: Using FastMCP with UV (Recommended)

```json
{
  "mcpServers": {
    "binance": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/Users/YourUsername/Documents/code/MCP/binance-mcp",
        "run",
        "fastmcp",
        "run",
        "main.py"
      ]
    }
  }
}
```

> **Note:** Make sure the `.env` file is in the project directory. The `uv run fastmcp run` command will automatically handle dependencies and environment setup.

#### Method 2: Using Python Directly

```json
{
  "mcpServers": {
    "binance": {
      "command": "python",
      "args": [
        "C:/Users/YourUsername/Documents/code/MCP/binance-mcp/main.py"
      ],
      "env": {
        "BINANCE_API_KEY": "your_api_key_here",
        "BINANCE_API_SECRET": "your_api_secret_here",
        "BINANCE_ENVIRONMENT": "production"
      }
    }
  }
}
```

#### Method 3: Using UV without FastMCP

```json
{
  "mcpServers": {
    "binance": {
      "command": "uv",
      "args": [
        "--directory",
        "C:/Users/YourUsername/Documents/code/MCP/binance-mcp",
        "run",
        "python",
        "main.py"
      ]
    }
  }
}
```

### Restart Claude Desktop

After updating the configuration, completely quit and restart Claude Desktop for changes to take effect.

## 🧪 Testing the Server

Before integrating with Claude Desktop, you can test the server locally:

```bash
# Start development server with inspector UI
uv run fastmcp dev main.py
```

This will:
1. Start the MCP server
2. Open a web inspector at `http://localhost:5173`
3. Allow you to test all tools interactively
4. Auto-reload when you make code changes

**Inspector Features:**
- 📋 List all available tools
- 🔧 Test tools with custom parameters
- 📊 See real-time request/response data
- 🐛 Debug issues before deploying to Claude

## 📖 Example Queries

Once integrated with Claude, you can ask:

- "What's my current portfolio across all accounts?"
- "Show me my open orders on futures"
- "What's the current price of BTCUSDT?"
- "Get my spot trading history for ETHUSDT"
- "Show me my recent futures PnL"
- "What are the latest Binance announcements?"
- "Check my margin account status"
- "Show my deposit history for the last 20 transactions"

## 🔒 Security Best Practices

1. **Read-Only Keys:** Only enable "Enable Reading" permission on your API keys
2. **Never Share:** Keep your API keys private and never commit them to version control
3. **IP Whitelist:** Consider restricting API key access to specific IP addresses in Binance settings
4. **Regular Rotation:** Periodically rotate your API keys for enhanced security
5. **Monitor Usage:** Regularly check your API key usage in Binance

## 🌐 Testnet Support

To use Binance Testnet for testing:

1. Create testnet API keys at [Binance Testnet](https://testnet.binance.vision/)
2. Set `BINANCE_ENVIRONMENT=testnet` in your `.env` file

## 🛠️ Development

### Project Structure

```
binance-mcp/
├── main.py              # Main MCP server with all tools
├── pyproject.toml       # Project dependencies
├── .env                 # Your API credentials (not committed)
├── .env.example         # Example environment file
├── .gitignore          # Git ignore rules
├── LICENSE              # MIT License
└── README.md           # This file
```

### Development Workflow

```bash
# 1. Install dependencies
uv sync

# 2. Create .env file with your API keys
cp .env.example .env
# Edit .env with your actual keys

# 3. Start development server
uv run fastmcp dev main.py

# 4. Open the inspector UI (opens automatically)
# http://localhost:5173

# 5. Make changes to main.py - server auto-reloads!
```

### Useful Commands

```bash
# Development mode (with inspector & auto-reload)
uv run fastmcp dev main.py

# Production mode (for Claude Desktop)
uv run fastmcp run main.py

# Install new dependencies
uv add package-name

# Update dependencies
uv sync

# Run linting (if configured)
uv run ruff check main.py
```

### Adding New Tools

To add a new tool, use the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def your_new_tool(param: str) -> str:
    """
    Description of your tool.
    
    Args:
        param: Description of parameter
    
    Returns:
        Markdown formatted result
    """
    # Your implementation
    return "Result in Markdown format"
```

**After adding a tool:**
1. The dev server will auto-reload
2. Test it in the inspector UI
3. Restart Claude Desktop to use it there

## 📝 API Rate Limits

Binance has rate limits on API requests:
- **Spot:** 1200 requests per minute
- **Futures:** 2400 requests per minute
- **Other endpoints:** Varies by endpoint

This server respects these limits. Avoid making excessive requests in a short time.


**This server is READ-ONLY and cannot execute trades, transfers, or withdrawals.**

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**MIT License Summary:**
- ✅ Commercial use
- ✅ Modification
- ✅ Distribution
- ✅ Private use
- ⚠️ No liability
- ⚠️ No warranty

## 🆘 Troubleshooting

### "API keys not configured" error
- Ensure your `.env` file exists and contains valid API credentials
- Check that environment variables are loaded correctly

### "Signature verification failed" error
- Verify your API secret is correct
- Ensure your system clock is synchronized (Binance API requires accurate time)

### "Permission denied" errors
- Confirm "Enable Reading" permission is enabled on your API key
- Some endpoints may require additional permissions

### Connection errors
- Check your internet connection
- Verify you're not behind a restrictive firewall
- Try using testnet to isolate issues

## 📞 Support

For issues and questions:
1. Check the [Binance API Documentation](https://binance-docs.github.io/apidocs/spot/en/)
2. Review closed issues in this repository
3. Open a new issue with details about your problem

---

**Happy Trading! 📈**

