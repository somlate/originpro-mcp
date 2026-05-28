"""
OriginPro MCP Server
====================
Exposes OriginLab OriginPro automation via the Model Context Protocol (MCP).
Requires Origin 2021+ and the `originpro` Python package (COM-based, Windows only).

Install:  pip install -r requirements.txt
Run:      python originpro_mcp_server.py

Color Index Reference (set via -c or -pfb flag):
  0=Black, 1=Black, 2=Red, 3=Green, 4=Blue, 5=Cyan, 6=Magenta,
  7=Yellow, 8=Olive, 9=Navy, 10=Purple, 11=Maroon,
  12=Dark Green, 13=Teal, 14=Dark Blue, 15=Orange,
  16=Violet, 17=Rose, 18=White, 19=Light Gray, 20=Gray,
  21=Light Yellow, 22=Light Cyan, 23=Light Pink,
  24=Dark Gray, 25-63=Black (unused)

Symbol Type Reference (set via -k flag):
  0=None, 1=Square, 2=Circle, 3=Up Triangle, 4=Down Triangle,
  5=Diamond, 6=Plus (+), 7=X, 8=Asterisk (*), 9=H-Line,
  10=V-Bar, 11=Small Square, 14=Right Arrow,
  15=Left Triangle (filled), 16=Right Triangle (filled),
  17=Hexagon, 18=Star (5-pt), 19=Pentagon, 20=Circle with Dot

Line Style Reference (set via -d flag):
  0=None, 1=Solid, 2=Short Dash, 3=Dot, 4=Dash-Dot,
  5=Dash-Dot-Dot, 6=Long Dash, 7=Long Dash-Dot, 8=Long Dash-Dot-Dot,
  9=Sparse Dot

Line Width (set via -w flag, unit = 1/100 pt):
  50=0.5pt, 100=1pt, 150=1.5pt, 200=2pt, 250=2.5pt, 300=3pt, 500=5pt

Plot Type for add_plot (set via type parameter):
  'l'=Line, 's'=Scatter, 'y'=Line+Symbol, 'c'=Column, '?'=Auto(Template)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import originpro as op
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# MCP server setup
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "OriginPro MCP",
    instructions="Control OriginLab OriginPro for scientific graphing and data analysis",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_initialized = False


def _kill_origin() -> None:
    """Force-kill any lingering Origin background processes."""
    for proc in ["Origin.exe", "Origin64.exe"]:
        subprocess.run(
            ["taskkill", "/f", "/im", proc],
            capture_output=True,
            text=True,
        )
    time.sleep(0.5)


def _ensure_origin() -> None:
    """Ensure Origin is running and ready, cleaning up stale processes first."""
    global _initialized
    if not _initialized:
        _kill_origin()
        op.set_show(True)
        _initialized = True


def _page_lookup(name: str | None, page_type: str | None = None) -> Any:
    """Resolve a page short name to an Origin page object."""
    all_pages = list(op.pages())
    if name is None:
        return all_pages[0] if all_pages else None
    candidates = [p for p in all_pages if p.name == name]
    if page_type:
        candidates = [p for p in candidates if p.type_name == page_type]
    if not candidates:
        avail = [p.name for p in all_pages]
        raise ValueError(f"Page '{name}' not found. Available: {avail}")
    return candidates[0]


def _origin_cleanup() -> None:
    """Gracefully exit Origin then kill lingering processes."""
    try:
        op.exit()
    except Exception:
        pass
    time.sleep(1)
    _kill_origin()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def new_project() -> str:
    """Create a new Origin project, discarding unsaved work."""
    _ensure_origin()
    op.new()
    return "New project created."


@mcp.tool()
def open_project(file_path: str) -> str:
    """Open an existing Origin project (.OPJU or .OPJ) file.

    Args:
        file_path: Absolute path to the project file.
    """
    _ensure_origin()
    p = Path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"
    op.open(str(p.resolve()))
    return f"Opened project: {p.name}"


@mcp.tool()
def save_project(file_path: str) -> str:
    """Save the current Origin project to a file.

    Args:
        file_path: Absolute path for the .OPJU file.
    """
    _ensure_origin()
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    op.save(str(p.resolve()))
    return f"Project saved to: {file_path}"


@mcp.tool()
def list_pages() -> str:
    """List all pages (worksheets, graphs, matrices) in the current project."""
    _ensure_origin()
    pages = list(op.pages())
    if not pages:
        return "No pages open."

    lines = ["# | Type    | Short Name | Long Name"]
    lines.append("-" * 50)
    for i, p in enumerate(pages):
        lines.append(f"{i} | {p.type_name:8s} | {p.name:10s} | {p.long_name()}")
    return "\n".join(lines)


@mcp.tool()
def activate_page(name: str) -> str:
    """Switch to a specific page by its short name.

    Args:
        name: Short name of the page (e.g. 'Book1', 'Graph1').
    """
    _ensure_origin()
    p = _page_lookup(name)
    p.set_active()
    return f"Activated page: {p.name} ({p.type_name})"


@mcp.tool()
def set_sheet_data(
    sheet_name: str | None,
    columns: list[dict[str, Any]],
) -> str:
    """Set data in a worksheet.

    Creates a new worksheet if *sheet_name* is None, otherwise uses the
    existing one.  Each column dict must have:

        {"name": "Col Name", "values": [1, 2, 3, ...]}

    If columns have different lengths the shorter ones are padded with
    missing values.

    Args:
        sheet_name: Optional short name of an existing worksheet.
        columns:    List of column definitions.
    """
    _ensure_origin()

    if sheet_name:
        wks = op.find_sheet(sheet_name)
        if wks is None:
            existing = [p.name for p in op.pages()]
            return f"Sheet '{sheet_name}' not found. Available: {existing}"
        wks.reset()
    else:
        wks = op.new_sheet("w")

    ncols = len(columns)
    max_rows = max((len(c["values"]) for c in columns), default=0)

    for i, col in enumerate(columns):
        vals = col["values"] if col.get("values") else []
        wks.from_list(i, vals, col["name"])
    # Set column designations: first = X, rest = Y
    if ncols > 0:
        spec = "x" + "y" * (ncols - 1)
        wks.cols_axis(spec)

    sn = wks.lname or str(wks)
    return f"Data set in worksheet '{sn}' — {ncols} column(s), {max_rows} row(s)"


@mcp.tool()
def get_data(sheet_name: str | None = None) -> str:
    """Return data from a worksheet as JSON.

    Args:
        sheet_name: Short name of the worksheet (default: active sheet).
    """
    _ensure_origin()
    if sheet_name:
        wks = op.find_sheet(sheet_name)
        if wks is None:
            return f"Sheet '{sheet_name}' not found."
    else:
        wks = op.find_sheet()
        if wks is None:
            return "No active worksheet."

    import json

    rows = wks.to_list()
    return json.dumps(rows, ensure_ascii=False, default=str)


@mcp.tool()
def import_csv(
    file_path: str,
    sheet_name: str | None = None,
) -> str:
    """Import a CSV or TXT file into a worksheet.

    Args:
        file_path:  Absolute path to the data file.
        sheet_name: Optional target worksheet short name (creates new if None).
    """
    _ensure_origin()
    p = Path(file_path)
    if not p.exists():
        return f"File not found: {file_path}"

    if sheet_name:
        wks = op.find_sheet(sheet_name)
        if wks is None:
            return f"Sheet '{sheet_name}' not found."
    else:
        wks = op.new_sheet("w")

    wks.import_file(str(p.resolve()))
    sn = wks.lname or str(wks)
    return f"Imported '{p.name}' into worksheet '{sn}' ({wks.cols} column(s), {wks.rows} row(s))"


PLOT_TYPE_MAP = {
    "line": "l",
    "scatter": "s",
    "line+symbol": "y",
    "column": "c",
}


@mcp.tool()
def create_plot(
    sheet_name: str,
    x_column: int,
    y_columns: list[int],
    plot_type: str = "line+symbol",
    graph_name: str | None = None,
) -> str:
    """Create a plot from worksheet columns.

    Args:
        sheet_name: Short name of the source worksheet.
        x_column:   Zero-based index of the X column (-1 for auto index).
        y_columns:  Zero-based indices of Y columns to plot.
        plot_type:  Plot type: line, scatter, line+symbol, column, bar, area,
                    stacked_column, stacked_bar, pie, histogram, box, 3d_bar,
                    3d_surface, contour, heatmap, waterfall.
        graph_name: Optional short name for the new graph page.
    """
    _ensure_origin()
    wks = op.find_sheet(sheet_name)
    if wks is None:
        existing = [p.name for p in op.pages()]
        return f"Sheet '{sheet_name}' not found. Available: {existing}"

    lt_type = PLOT_TYPE_MAP.get(plot_type, "?")

    gp = op.new_graph(graph_name) if graph_name else op.new_graph()
    gl = gp[0]

    for yi in y_columns:
        if x_column >= 0:
            gl.add_plot(wks, yi, x_column, type=lt_type)
        else:
            gl.add_plot(wks, yi, type=lt_type)

    try:
        gl.rescale()
    except Exception:
        pass

    gn = gp.name or str(gp)
    return f"Plot created in graph '{gn}' — type={plot_type}, Y columns={y_columns}"


@mcp.tool()
def export_graph(
    file_path: str,
    graph_name: str | None = None,
    width: int = 800,
    image_type: str = "png",
) -> str:
    """Export a graph page to an image file.

    Args:
        file_path:  Absolute path for the output image (extension sets format).
        graph_name: Short name of the graph page (default: active).
        width:      Image width in pixels.
        image_type: Image format: png, jpg, tif, bmp, svg, pdf, eps.
    """
    _ensure_origin()
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if graph_name:
        gp = _page_lookup(graph_name, "Graph")
    else:
        graph_pages = [p for p in op.pages() if p.type_name == "Graph"]
        gp = graph_pages[0] if graph_pages else None
        if gp is None:
            return "No graph page found."

    try:
        gp.save_fig(str(p.resolve()), type=image_type, width=width)
    except Exception as e:
        return f"Export failed: {e}"

    return f"Graph exported to: {file_path} ({width}px wide)"


@mcp.tool()
def set_column_labels(
    sheet_name: str,
    labels: dict[str, str],
) -> str:
    """Set long names on worksheet columns. Used for axis labels and legend text.

    Args:
        sheet_name: Short name of the worksheet.
        labels:     Dict mapping column letter (A, B, C...) or index to long name.
                    Example: {"B": "长期平均值", "C": "新方法"}
    """
    _ensure_origin()
    wks = op.find_sheet(sheet_name)
    if wks is None:
        return f"Sheet '{sheet_name}' not found."

    for col, name in labels.items():
        wks.set_label(col, name)
    return f"Set long names on {len(labels)} columns."


@mcp.tool()
def set_axis_labels(
    graph_name: str,
    x_label: str | None = None,
    y_label: str | None = None,
    x_font_size: int | None = None,
    y_font_size: int | None = None,
) -> str:
    """Set axis labels and font sizes for a graph.

    Args:
        graph_name:  Short name of the graph page.
        x_label:     X axis label text.
        y_label:     Y axis label text.
        x_font_size: X axis label font size in points.
        y_font_size: Y axis label font size in points.
    """
    _ensure_origin()
    gp = _page_lookup(graph_name, "Graph")
    gl = gp[0]

    if x_label is not None:
        x_ax = gl.axis("x")
        x_ax.title = x_label
    if y_label is not None:
        y_ax = gl.axis("y")
        y_ax.title = y_label
    if x_font_size is not None:
        op.lt_exec(f"layer1.x.axes.title.font.size = {x_font_size}")
    if y_font_size is not None:
        op.lt_exec(f"layer1.y.axes.title.font.size = {y_font_size}")

    parts = []
    if x_label:
        parts.append(f"X='{x_label}'")
    if y_label:
        parts.append(f"Y='{y_label}'")
    return "Axis labels set: " + ", ".join(parts) if parts else "No changes."


@mcp.tool()
def customize_plot(
    graph_name: str,
    plot_index: int,
    color: int | None = None,
    symbol_type: int | None = None,
    symbol_size: int | None = None,
    symbol_fill: bool | None = None,
    line_width: int | None = None,
) -> str:
    """Customize the appearance of a specific data plot in a graph.

    Args:
        graph_name:  Short name of the graph page.
        plot_index:  Zero-based index of the data plot to customize.
        color:       Color index. Common: 2=Red, 3=Green, 4=Blue, 5=Cyan,
                     6=Magenta, 7=Yellow, 15=Orange, 18=White, 19=Light Gray,
                     20=Gray, 24=Dark Gray. Full list in module docstring.
        symbol_type: Symbol type. Common: 1=Square, 2=Circle, 3=Up Triangle,
                     4=Down Triangle, 5=Diamond, 7=Star. Full list in module docstring.
                     Only works when plot was created with plot_type='line+symbol' or 'scatter'.
        symbol_size: Symbol size in points.
        symbol_fill: Whether symbols are filled (True) or open (False).
        line_width:  Line width in 1/100 pt (e.g. 250 = 2.5 pt).
    """
    _ensure_origin()
    gp = _page_lookup(graph_name, "Graph")
    gl = gp[0]
    plots = gl.plot_list()

    if plot_index >= len(plots):
        return f"Plot index {plot_index} out of range. Graph has {len(plots)} plots."

    p = plots[plot_index]
    cmds = []
    if color is not None:
        cmds.append(f"-c {color}")
    if symbol_type is not None:
        cmds.append(f"-k {symbol_type}")
    if line_width is not None:
        cmds.append(f"-w {line_width}")
    if cmds:
        p.set_cmd(*cmds)

    info_parts = [f"Plot {plot_index} ({p.name})"]
    if color is not None:
        info_parts.append(f"color={color}")
    if symbol_type is not None:
        info_parts.append(f"symbol_type={symbol_type}")
    if line_width is not None:
        info_parts.append(f"line_width={line_width}")
    return "Customized: " + ", ".join(info_parts)


@mcp.tool()
def set_legend(
    graph_name: str,
    labels: list[str] | None = None,
    use_long_names: bool = True,
) -> str:
    """Configure the legend for a graph.

    Args:
        graph_name:    Short name of the graph page.
        labels:        Optional list of legend labels (one per data plot).
                       If None and use_long_names=True, uses column long names.
        use_long_names: If True, legend uses worksheet column long names.
                        Set long names on columns first with set_sheet_data or LabTalk.
    """
    _ensure_origin()
    gp = _page_lookup(graph_name, "Graph")
    gl = gp[0]

    op.lt_exec("layer1.legend show")

    if use_long_names:
        op.lt_exec('layer1.legend.label$ = "long"')
        return "Legend set to use column long names. Ensure long names are set on worksheet columns."

    if labels:
        text = "\\n".join(labels)
        op.lt_exec(f'layer1.legend.text$ = "{text}"')
        return f"Legend set with {len(labels)} labels."

    return "Legend shown with default labels."


@mcp.tool()
def linear_fit(
    sheet_name: str,
    x_column: int = 0,
    y_column: int = 1,
    fit_through_zero: bool = False,
) -> str:
    """Perform linear regression on a worksheet column pair.

    Args:
        sheet_name:       Short name of the worksheet.
        x_column:         Zero-based X column index.
        y_column:         Zero-based Y column index.
        fit_through_zero: Force intercept at zero.
    """
    _ensure_origin()
    wks = op.find_sheet(sheet_name)
    if wks is None:
        return f"Sheet '{sheet_name}' not found."

    from originpro import Analysis

    pe = op.new_sheet("w", "<linear fit parameters>")
    Analysis.lr(
        wks,
        pe,
        xCol=x_column,
        yCol=y_column,
        throughZero=int(fit_through_zero),
    )

    rows = pe.to_list()
    result = f"Linear fit on '{sheet_name}' (col {x_column} → col {y_column})\n"
    for r in rows:
        result += f"  {r[0]} = {r[1]}\n"

    pe.destroy()
    return result


@mcp.tool()
def statistics(
    sheet_name: str,
    column: int = 1,
) -> str:
    """Compute descriptive statistics on a column.

    Args:
        sheet_name: Short name of the worksheet.
        column:     Zero-based column index.
    """
    _ensure_origin()
    wks = op.find_sheet(sheet_name)
    if wks is None:
        return f"Sheet '{sheet_name}' not found."

    from originpro import Analysis

    pd = op.new_sheet("w", "<stats results>")
    Analysis.descriptive_stats(wks, pd, col=column)

    rows = pd.to_list()
    result = f"Descriptive statistics for '{sheet_name}', col {column}:\n"
    for r in rows:
        result += f"  {r[0]} = {r[1]}\n"

    pd.destroy()
    return result


@mcp.tool()
def run_labtalk(script: str) -> str:
    """Execute an arbitrary LabTalk script in Origin.

    Args:
        script: LabTalk script text.
    """
    _ensure_origin()
    try:
        op.lt_exec(script)
        return f"LabTalk executed:\n{script}"
    except Exception as e:
        return f"LabTalk error: {e}"


@mcp.tool()
def cleanup() -> str:
    """Force-kill all Origin background processes. Call this if Origin fails to start."""
    _kill_origin()
    return "Origin processes cleaned up."


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("originpro://pages", description="List of all pages in the current project")
def pages_resource() -> str:
    if not _initialized:
        return "[]"
    import json

    pages = list(op.pages())
    if not pages:
        return "[]"

    info = []
    for p in pages:
        info.append(
            {
                "name": p.name,
                "long_name": p.long_name(),
                "type": p.type_name,
            }
        )
    return json.dumps(info, ensure_ascii=False)


@mcp.resource("originpro://version", description="OriginPro version information")
def version_resource() -> str:
    _ensure_origin()
    try:
        v = op.get_app().GetVersion()
        return f"OriginPro version: {v}"
    except Exception:
        return "OriginPro version: unknown"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting OriginPro MCP server...", file=sys.stderr)
    try:
        mcp.run()
    finally:
        _origin_cleanup()
