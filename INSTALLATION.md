# Installation Instructions

## Quick Install

1. **Download** the `ErcotMCPExtension.mcpb` file (90MB)
2. **Install** in Claude Code:
   - Open Claude Code
   - Go to Settings → Extensions
   - Click "Install from .mcpb file"
   - Select `ErcotMCPExtension.mcpb`

## Prerequisites

**Python 3.9 or higher** must be installed on your system. The extension comes with all Python dependencies bundled in the `lib/` folder - no additional installations needed!

To verify your Python version:
```bash
python3 --version
```

## How It Works

The extension includes all required dependencies (mcp, pandas, requests, pydantic, scikit-learn, numpy) bundled in the `lib/` folder. The manifest is configured to use your system Python with `PYTHONPATH` pointing to the bundled libraries, making it completely portable

## API Credentials

You'll need ERCOT API credentials. Get them at: https://apiexplorer.ercot.com/

After registering, you'll receive three credentials. Configure them in the extension settings:
- **API User Name**: Your ERCOT username (email)
- **API Password**: Your ERCOT password
- **API Key**: Your ERCOT subscription key (Ocp-Apim-Subscription-Key)

All three credentials are required for the extension to work.

## Troubleshooting

If the extension fails to connect:
1. Verify Python 3.9+ is installed: `python3 --version`
2. Check that the .mcpb file was installed (not unpacked extension)
3. Check the extension logs in Claude Code developer settings
4. Verify the extension shows as "Connected" in Settings → Extensions

### Common Issues

**"Module not found" errors**: This usually means the `lib/` folder wasn't properly installed. Make sure you're installing from the .mcpb file, not as an unpacked extension.

**"Connection failed"**: Check the logs for Python path issues. The extension requires `/opt/homebrew/bin/python3` or will try to use system python3.
