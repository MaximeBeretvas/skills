#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml"]
# ///
"""Render a Hex project export (yaml) as compact Markdown for an AI agent to read.

Read-only, one-way: never reimported into Hex. Strips Hex's UI/layout noise
(column widths, pivot-table specs, cellId UUIDs, ...) and keeps the logic
(SQL/Python source, filter definitions, metric formulas, viz field mappings).

Usage: uv run Scripts/hex_yaml_compact.py <path-to-hex.yaml>
"""

import re
import sys
from pathlib import Path

import yaml

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
CONNECTION_COMMENT_RE = re.compile(r"dataConnectionId:\s*\S+\s*#\s*(.+)")

# ponytail: blocklist, not allowlist — new noisy keys Hex adds later just need
# adding here rather than every formatter growing exceptions.
NOISE_KEYS = {
    "tableDisplayConfig", "displayTableConfig", "columnProperties",
    "pivotColumnWidth", "seriesId", "queryPath", "hideIcons", "wrapText",
    "displayFormat", "defaultColumnWidth", "pinnedColumns", "hiddenColumns",
    "pinIndexColumns", "showAggregations", "columnAggregations",
    "columnOrdering", "customColumnOrdering", "chartConfig", "colorMappings",
    "rowTotals", "columnTotals", "rowSubtotals", "columnSubtotals",
    "visualizationType", "viewType", "cellId", "height",
}

EMPTY = (None, "", [], {})

# Populated once in main() from the whole document; render_sql reads it to
# annotate each SQL cell with who consumes its result dataframe.
_CONSUMER_INDEX = {}


def strip_noise(obj):
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if key in NOISE_KEYS or (isinstance(value, str) and UUID_RE.match(value)):
                continue
            cleaned = strip_noise(value)
            if cleaned in EMPTY:
                continue
            out[key] = cleaned
        return out
    if isinstance(obj, list):
        return [v for v in (strip_noise(item) for item in obj) if v not in EMPTY]
    return obj


def heading(level, text):
    return f"{'#' * level} {text}"


def label_of(cell):
    return cell.get("cellLabel") or "(unlabeled)"


def render_sql(cell, level):
    cfg = cell.get("config") or {}
    result_var = cfg.get("resultVariableName")
    lines = [heading(level, f"{label_of(cell)} — SQL"), ""]
    if result_var:
        lines += [f"_result: `{result_var}`_", ""]
    consumers = _CONSUMER_INDEX.get(result_var) if result_var else None
    if consumers:
        served = ", ".join(f"{consumer_label} ({consumer_type})" for consumer_label, consumer_type in consumers)
        lines += [f"_serves: {served}_", ""]
    lines += ["```sql", (cfg.get("source") or "").rstrip(), "```", ""]
    return lines


def render_code(cell, level):
    cfg = cell.get("config") or {}
    return [heading(level, f"{label_of(cell)} — CODE"), "",
            "```python", (cfg.get("source") or "").rstrip(), "```", ""]


def render_input(cell, level):
    cfg = cell.get("config") or {}
    lines = [heading(level, f"{label_of(cell)} — INPUT ({cfg.get('inputType', '?')})"), ""]
    lines.append(f"- variable: `{cfg.get('name')}`")
    default = cfg.get("defaultValue")
    if default not in EMPTY:
        lines.append(f"- default: `{default}`")
    multi = (cfg.get("options") or {}).get("multiValueOptions") or {}
    df_name, col_name = (multi.get("dfName"), multi.get("columnName")) if isinstance(multi, dict) else (None, None)
    if df_name and col_name:
        lines.append(f"- filters values from `{df_name}['{col_name}']`")
    elif df_name:
        lines.append(f"- filters values from `{df_name}`")
    lines.append("")
    return lines


def render_markdown(cell, level):
    source = (cell.get("config") or {}).get("source") or ""
    if not source.strip():
        return []
    return [heading(level, f"{label_of(cell)} — MARKDOWN"), "", source.rstrip(), ""]


def flatten_rich_text_node(node):
    parts = []
    if "text" in node:
        parts.append(node["text"])
    for child in node.get("children") or []:
        parts.append(flatten_rich_text_node(child))
    return "".join(parts)


def render_text(cell, level):
    nodes = (cell.get("config") or {}).get("richText") or []
    lines = [line for node in nodes if (line := flatten_rich_text_node(node).strip())]
    if not lines:
        return []
    return [heading(level, f"{label_of(cell)} — TEXT"), "", *lines, ""]


def render_metric(cell, level):
    cfg = cell.get("config") or {}
    title = cfg.get("title") or label_of(cell)
    lines = [heading(level, f"{title} — METRIC"), ""]
    lines.append(f"- value: `{cfg.get('valueAggregate')}({cfg.get('valueColumn')})` "
                 f"from `{cfg.get('valueVariableName')}`")
    if cfg.get("valueResultVariable"):
        lines.append(f"- result variable: `{cfg['valueResultVariable']}`")
    lines.append("")
    return lines


def render_field_table(fields):
    """`field | column | channel | aggregation` table shared by EXPLORE and CHARTV2."""
    if not fields:
        return []
    lines = ["| field | column | channel | aggregation |", "|---|---|---|---|"]
    for f in fields:
        lines.append(f"| {f.get('title') or f.get('value')} | `{f.get('value')}` "
                     f"| {f.get('channel', '')} | {f.get('aggregation', '')} |")
    lines.append("")
    return lines


def calc_lines(cfg):
    """calc-column definitions, wherever the cell type nests them."""
    lines = []
    calc_sources = [cfg.get("calcs"), (cfg.get("displayTableConfig") or {}).get("calcs"),
                     (cfg.get("tableDisplayConfig") or {}).get("calcs")]
    for calcs in calc_sources:
        for calc in (calcs or {}).get("calcColumns") or []:
            lines.append(f"- calc `{calc.get('name')}` = `{calc.get('expression')}`")
    return lines


def dataframe_ref_name(value):
    """A dataframe reference is either a plain var name, or (for cells pointing
    directly at a raw source table rather than a SQL cell's result) a dict
    carrying the resolved name under `dataframeName`."""
    if isinstance(value, dict):
        return value.get("dataframeName")
    return value or None


def render_explore(cell, level):
    cfg = cell.get("config") or {}
    lines = [heading(level, f"{label_of(cell)} — EXPLORE"), ""]
    df_name = dataframe_ref_name(cfg.get("dataframe"))
    if df_name:
        lines += [f"_visualizing: `{df_name}`_", ""]

    lines += render_field_table((cfg.get("spec") or {}).get("fields"))
    lines += calc_lines(cfg)
    lines.append("")
    return lines


def render_table_display(cell, level):
    cfg = cell.get("config") or {}
    lines = [heading(level, f"{label_of(cell)} — TABLE_DISPLAY"), ""]
    if cfg.get("dataFrameVariableName"):
        lines += [f"_displaying: `{cfg['dataFrameVariableName']}`_", ""]
    if cfg.get("resultVariable"):
        lines.append(f"- result variable: `{cfg['resultVariable']}`")
    lines += calc_lines(cfg)
    lines.append("")
    return lines


def chartv2_dataframe(chart_spec):
    for layer in (chart_spec or {}).get("layers") or []:
        df_name = dataframe_ref_name(layer.get("dataFrame"))
        if df_name:
            return df_name
    return None


def chartv2_fields(chart_spec):
    fields = []
    for layer in (chart_spec or {}).get("layers") or []:
        x_axis = layer.get("xAxis") or {}
        if x_axis.get("dataFrameColumn"):
            fields.append({"value": x_axis["dataFrameColumn"], "channel": "xAxis",
                            "aggregation": x_axis.get("timeUnit", "")})
        for series in layer.get("series") or []:
            axis = series.get("axis") or {}
            for column in series.get("dataFrameColumns") or []:
                fields.append({"value": column, "channel": series.get("type", "series"),
                               "aggregation": axis.get("aggregate", "")})
    return fields


# cellType -> function extracting the dataframe var it consumes, for build_consumer_index.
CONSUMER_DF_GETTERS = {
    "EXPLORE": lambda cfg: dataframe_ref_name(cfg.get("dataframe")),
    "CHARTV2": lambda cfg: chartv2_dataframe(cfg.get("chartSpec") or {}),
    "METRIC": lambda cfg: cfg.get("valueVariableName"),
    "TABLE_DISPLAY": lambda cfg: cfg.get("dataFrameVariableName"),
    "FILTER": lambda cfg: cfg.get("dataframeName"),
}


def build_consumer_index(cells):
    """dataframe var -> [(cellLabel, cellType)] of cells reading it, recursing into COLLAPSIBLE."""
    index = {}
    for cell in cells or []:
        cell_type = cell.get("cellType")
        cfg = cell.get("config") or {}
        getter = CONSUMER_DF_GETTERS.get(cell_type)
        df_name = getter(cfg) if getter else None
        if df_name:
            index.setdefault(df_name, []).append((label_of(cell), cell_type))
        if cell_type == "COLLAPSIBLE":
            for df_name, consumers in build_consumer_index(cfg.get("cells")).items():
                index.setdefault(df_name, []).extend(consumers)
    return index


def render_chartv(cell, level):
    cfg = cell.get("config") or {}
    chart_spec = cfg.get("chartSpec") or {}
    lines = [heading(level, f"{label_of(cell)} — CHARTV2"), ""]
    df_name = chartv2_dataframe(chart_spec)
    if df_name:
        lines += [f"_visualizing: `{df_name}`_", ""]
    lines += render_field_table(chartv2_fields(chart_spec))
    lines.append("")
    return lines


def render_filter(cell, level):
    cfg = cell.get("config") or {}
    lines = [heading(level, f"{label_of(cell)} — FILTER"), ""]
    if cfg.get("dataframeName"):
        lines += [f"_filtering: `{cfg['dataframeName']}`_", ""]
    for f in (cfg.get("filters") or {}).get("filters") or []:
        op = f.get("operation") or {}
        lines.append(f"- `{f.get('column')}` {op.get('op', '')} `{op.get('arg', '')}`")
    lines.append("")
    return lines


def render_component_import(cell, level):
    comp = (cell.get("config") or {}).get("component") or {}
    lines = [heading(level, f"{label_of(cell)} — COMPONENT_IMPORT"), ""]
    if comp:
        lines.append(f"- component: `{comp.get('id')}` (version {comp.get('version')})")
    lines.append("")
    return lines


def render_collapsible(cell, level):
    lines = [heading(level, f"{label_of(cell)} (group)"), ""]
    for sub in (cell.get("config") or {}).get("cells") or []:
        try:
            lines += render_cell(sub, level + 1)
        except Exception:
            lines += render_generic(sub, level + 1)
    return lines


def render_generic(cell, level):
    lines = [heading(level, f"{label_of(cell)} — {cell.get('cellType', 'UNKNOWN')}"), ""]
    cleaned = strip_noise(cell.get("config") or {})
    if cleaned:
        lines += ["```yaml", yaml.dump(cleaned, sort_keys=False).rstrip(), "```"]
    lines.append("")
    return lines


HANDLERS = {
    "SQL": render_sql,
    "CODE": render_code,
    "INPUT": render_input,
    "METRIC": render_metric,
    "EXPLORE": render_explore,
    "COLLAPSIBLE": render_collapsible,
    "MARKDOWN": render_markdown,
    "TEXT": render_text,
    "TABLE_DISPLAY": render_table_display,
    "CHARTV2": render_chartv,
    "FILTER": render_filter,
    "COMPONENT_IMPORT": render_component_import,
}


def render_cell(cell, level=2):
    handler = HANDLERS.get(cell.get("cellType"), render_generic)
    return handler(cell, level)


def render_meta(doc, raw_text):
    meta = doc.get("meta") or {}
    lines = []
    if meta.get("title"):
        lines.append(f"# {meta['title']}")
    if meta.get("description"):
        lines.append(f"_{meta['description']}_")
    connections = CONNECTION_COMMENT_RE.findall(raw_text.split("cells:", 1)[0])
    if connections:
        lines.append(f"connections: {', '.join(c.strip() for c in connections)}")
    lines.append("")
    return lines


def main():
    if len(sys.argv) != 2:
        print("usage: hex_yaml_compact.py <path-to-hex.yaml>", file=sys.stderr)
        raise SystemExit(1)

    raw_text = Path(sys.argv[1]).read_text()
    doc = yaml.safe_load(raw_text)

    global _CONSUMER_INDEX
    _CONSUMER_INDEX = build_consumer_index(doc.get("cells") or [])

    out = render_meta(doc, raw_text)
    for cell in doc.get("cells") or []:
        try:
            out += render_cell(cell)
        except Exception:
            out += render_generic(cell, 2)

    print("\n".join(out).rstrip() + "\n", end="")


if __name__ == "__main__":
    main()
