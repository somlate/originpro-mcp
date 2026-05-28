# OriginPro MCP Server

A Model Context Protocol (MCP) server for controlling [OriginLab OriginPro](https://www.originlab.com/) — the scientific graphing and data analysis software. This allows AI assistants like Claude to create publication-quality graphs, perform data analysis, and automate OriginPro workflows.

> **Windows only.** OriginPro 2021+ and the `originpro` Python package (COM-based) are required.

## Features

- **Project management** — create, open, save Origin projects (.OPJU/.OPJ)
- **Data import** — set worksheet data directly or import CSV/TXT files
- **16+ plot types** — line, scatter, line+symbol, column, bar, area, stacked, pie, histogram, box, 3D, contour, heatmap, waterfall
- **Plot customization** — colors, symbol types, line widths, axis labels, legends (including CJK text)
- **Statistical analysis** — linear regression, descriptive statistics
- **Graph export** — PNG, JPG, TIFF, BMP, SVG, PDF, EPS
- **LabTalk scripting** — execute arbitrary Origin LabTalk scripts for advanced operations

## Prerequisites

1. **OriginPro 2021+** installed on Windows
2. **Python 3.10+**
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Setup

### Claude Code

Add to your Claude Code MCP config (`~/.claude/mcp.json`):

```json
{
  "mcpServers": {
    "originpro": {
      "command": "python",
      "args": ["C:\\path\\to\\originpro-mcp\\originpro_mcp_server.py"]
    }
  }
}
```

### Other MCP Clients

Run the server directly:

```bash
python originpro_mcp_server.py
```

## Available Tools (18)

| Tool | Description |
|------|-------------|
| `new_project` | Create a new Origin project |
| `open_project` | Open an existing .OPJU/.OPJ file |
| `save_project` | Save the current project |
| `list_pages` | List all pages in the project |
| `activate_page` | Switch to a specific page |
| `set_sheet_data` | Set data in a worksheet |
| `get_data` | Read data from a worksheet as JSON |
| `import_csv` | Import a CSV/TXT file |
| `create_plot` | Create a plot (16+ types) |
| `export_graph` | Export graph to image file |
| `set_column_labels` | Set column long names (for legends) |
| `set_axis_labels` | Set axis labels and font sizes |
| `customize_plot` | Set colors, symbols, line widths |
| `set_legend` | Configure legend (long names or custom text) |
| `linear_fit` | Linear regression |
| `statistics` | Descriptive statistics |
| `run_labtalk` | Execute arbitrary LabTalk script |
| `cleanup` | Kill lingering Origin processes |

## How It Works

The MCP server uses the `originpro` Python package, which communicates with OriginPro via COM automation (Windows only). The server exposes OriginPro's functionality through the Model Context Protocol, allowing AI assistants to control OriginPro programmatically.

## License

MIT
