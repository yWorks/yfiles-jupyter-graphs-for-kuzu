# yFiles Jupyter Graphs for Kuzu Agent Guide

Reference for coding agents working with `yfiles-jupyter-graphs-for-kuzu` (v2.x).

## Purpose

This package is a Kuzu adapter around [`yfiles-jupyter-graphs`](https://github.com/yWorks/yfiles-jupyter-graphs).
`KuzuGraphWidget` executes Cypher queries through a Kuzu connection, converts Kuzu node and relationship values into
the node and edge data expected by `GraphWidget`, applies Kuzu-specific mappings, and renders the resulting Jupyter
widget.

The package is intended for visualizing graph-shaped Cypher results. A query should return nodes and relationships,
usually by returning the variables in a pattern such as `RETURN s, r, t`.

## Install

```bash
pip install yfiles_jupyter_graphs_for_kuzu kuzu
```

The package requires `yfiles_jupyter_graphs~=2.0`. Install the Kuzu Python package separately when it is not already
available in the application environment.

**Google Colab:** enable the custom widget manager before displaying the widget:

```python
try:
    import google.colab
    from google.colab import output
    output.enable_custom_widget_manager()
except:
    pass
```

## Core import pattern

```python
import kuzu
from yfiles_jupyter_graphs_for_kuzu import KuzuGraphWidget
```

## Minimal working example

```python
db = kuzu.Database("<path-to-db>")
connection = kuzu.Connection(db)

widget = KuzuGraphWidget(connection)
widget.show_cypher("MATCH (s)-[r]->(t) RETURN s, r, t LIMIT 20")
```

`show_cypher()` displays the widget itself; an additional `display()` call is normally not required.

## `KuzuGraphWidget` constructor

| Argument | Type | Notes | Default |
|---|---|---|---|
| `connection` | Kuzu connection-compatible object | Connection used to execute Cypher queries. | `None` |
| `widget_layout` | `ipywidgets.Layout` | General widget appearance through CSS attributes. | `None` |
| `overview_enabled` | `bool` | Enables the graph overview component. `None` uses the core widget default. | `None` |
| `context_start_with` | `str` | Side panel to open initially. | `None` |
| `license` | `dict` | Optional yFiles license configuration. | `None` |
| `layout` | `str` | Default automatic graph layout. | `"organic"` |

Supported layout strings are `circular`, `circular_straight_line`, `hierarchical`, `organic`, `interactive_organic`,
`orthogonal`, `radial`, `tree`, `map`, `orthogonal_edge_router`, and `organic_edge_router`.

The connection can be assigned after construction:

```python
widget.connection = connection
```

The older `get_connection()` and `set_connection()` methods are deprecated. Prefer the `connection` property.

## Query behavior

### `show_cypher(cypher, layout=None, **kwargs)`

`show_cypher` requires a configured connection. It calls `connection.execute(cypher, **kwargs)`, parses the returned
Kuzu `QueryResult`, creates a new `GraphWidget`, and displays it. The optional `layout` overrides the constructor's
default layout for that render only.

The query must return graph values that the parser can recognize:

- A node has `_label` and `_id`, and does not have `_src` and `_dst`.
- A relationship has `_label`, `_src`, and `_dst`.
- Recursive relationship results may contain `_nodes` and `_rels`; both collections are expanded.

The common form is:

```cypher
MATCH (s:User)-[r:Follows]->(t:User)
RETURN s, r, t
```

Queries that return only scalar columns, or do not return recognizable nodes and relationships, cannot produce a graph.
When parsing fails, the adapter logs a warning and returns without displaying the graph. Calling `show_cypher` without a
connection raises an exception.

The adapter sets `GraphWidget.directed = True` by default, so relationship direction is shown.

## Kuzu-to-graph conversion

The adapter produces dictionaries consumed by `GraphWidget`:

- Nodes receive an `id` formed from their Kuzu table label and primary-key value: `Label_primary-key`.
- Relationships receive `id`, `start`, and `end`; the endpoints are resolved from Kuzu `_src` and `_dst` references.
- Node and relationship `properties["label"]` contain the Kuzu table label or relationship type.
- Non-internal Kuzu fields that are declared in the corresponding table are copied to `properties`.
- `date` and `datetime` values are converted to ISO-8601 strings.

The parser calls `CALL TABLE_INFO(...) RETURN *` to determine primary-key and property columns. Kuzu node tables must
therefore expose their normal primary key metadata. Duplicate nodes and relationships in query results are collapsed
using their Kuzu table/offset identity.

For default node text, the adapter checks properties case-insensitively in this order: `name`, `title`, `text`,
`description`, `caption`, `label`. If none is present, the core widget's default behavior applies.

## Data-driven configuration

Configurations are stored on the `KuzuGraphWidget` instance and should be added before `show_cypher`. Node labels and
relationship types accept either one string or a list of strings. The special key `"*"` provides a fallback when no
more-specific configuration exists.

### Node configurations

```python
widget.add_node_configuration(
    "Movie",
    color="#2F6BFF",
    text="title",
    size=lambda node: (60, 60),
)
widget.add_node_configuration("Person", styles={"shape": "ellipse"})
```

`add_node_configuration(label, **kwargs)` supports `text`, `color`, `size`, `styles`, `property`, `type`,
`coordinate`, `scale_factor`, `position`, `layout`, `heat`, and `parent_configuration`. The `text` argument is mapped
to the core widget's `label` mapping. Supported node shapes include `ellipse`, `hexagon`, `hexagon2`, `octagon`,
`pill`, `rectangle`, `round-rectangle`, and `triangle`.

### Relationship configurations

```python
widget.add_relationship_configuration(
    "Rated",
    color="orange",
    thickness_factor=2,
    text=lambda relationship: f"Rating: {relationship['properties']['rating']}",
)
widget.add_relationship_configuration("*", styles={"directed": False})
```

`add_relationship_configuration(type, **kwargs)` supports `text`, `color`, `thickness_factor`, `styles`, `property`,
and `heat`. The `text` argument is mapped to the core widget's `label` mapping.

### Binding resolution

For a configured binding:

1. A callable is invoked with the graph item dictionary and its return value is used.
2. A non-dictionary string is looked up in `item["properties"]`.
3. If that property does not exist, the string is used as a constant.
4. Other values, including dictionaries, are used directly.

Consequently, a string that is both a property name and a desired constant resolves to the property. Use a callable such
as `lambda item: "label"` to force a constant string.

Configuration matching uses `item["properties"]["label"]`, which is the Kuzu node table label or relationship type.
The adapter's configuration mapper does not merge a wildcard configuration into a more-specific configuration; define
all bindings needed by a specific configuration explicitly.

### Removing configurations

```python
widget.del_node_configuration("Movie")
widget.del_relationship_configuration(["Rated", "Follows"])
```

Each method accepts one string or a list. Passing `"*"` clears the corresponding configuration dictionary.

## Grouping and nesting

Relationship-based nesting converts matching relationships into parent-child relationships and removes those edges from
the displayed graph:

```python
widget.add_parent_relationship_configuration("Contains")
widget.add_parent_relationship_configuration("MemberOf", reverse=True)
widget.show_cypher(query, layout="hierarchical")
```

`add_parent_relationship_configuration(type, reverse=False)` treats the relationship target as the parent by default.
With `reverse=True`, the source is treated as the parent. Lists are accepted. Remove rules with
`del_parent_relationship_configuration(type)`.

Node configurations can also create group nodes with `parent_configuration`:

```python
widget.add_node_configuration("Movie", parent_configuration="movies")
widget.add_node_configuration("Person", parent_configuration={"text": "people", "color": "#9F4499"})
```

A string is interpreted as a node property when it matches one; otherwise it is a constant group label. A callable can
compute either a string or a group configuration dictionary from the node.

## Introspection and layout mappings

After rendering, `widget.graph_widget` returns the most recent underlying `GraphWidget`, or `None` before the first
successful render. `widget.query_result` returns the most recent Kuzu query result.

`node_cell_mapping` is a property forwarded to the underlying widget before each render. It may be a property name or a
callable returning a `(row, column)` tuple for a node, and is used by supported automatic layouts:

```python
widget.node_cell_mapping = lambda node: (node["properties"].get("category", 0), 0)
```

The older `get_node_cell_mapping()`, `set_node_cell_mapping()`, and `del_node_cell_mapping()` methods are deprecated.

## Delegated core-widget features

The rendered object is an instance of `yfiles_jupyter_graphs.GraphWidget`, available as `widget.graph_widget`. The core
widget supplies the toolbar, selection, search, neighborhood, overview, labels, styles, layouts, and additional mapping
APIs. Consult the [core widget agent guide](https://github.com/yWorks/yfiles-jupyter-graphs/blob/main/agent-guide.md)
for those features.

When a new Cypher query is rendered, this adapter creates a new `GraphWidget` and reapplies its stored Kuzu mappings.
Changes made directly to `widget.graph_widget` should therefore be treated as render-specific unless they are also
represented by an adapter configuration or property.

## Implementation caveats

- Return nodes and relationships from Cypher; arbitrary tabular results are not supported by the graph parser.
- Query-result fields with leading underscores are Kuzu internals and are not copied as user-facing properties.
- The parser performs schema lookups with `TABLE_INFO` while converting results, so the connection must remain usable for
  those additional queries.
- The adapter creates a fresh underlying `GraphWidget` for each call to `show_cypher`.
- Use `hierarchical` when nesting is required; relationship-based nesting removes the matching relationship edges from
  the displayed graph.
