As of October 2025, the Kuzu project is stopped.  yFiles Jupyter Graphs for Kuzu works for the 2 forks of the project: Ladybug & Ryugraph
# yFiles Jupyter Graphs for Kuzu - Ladybug & Ryugraph
![A screenshot showing the yFiles graph widget for Kuzu in a jupyter lab notebook](https://raw.githubusercontent.com/yWorks/yfiles-jupyter-graphs-for-kuzu/kuzu/images/example.png)

[![PyPI version](https://badge.fury.io/py/yfiles-jupyter-graphs-for-kuzu.svg)](https://badge.fury.io/py/yfiles-jupyter-graphs-for-kuzu)

Easily visualize a [Ladybug]([https://kuzudb.com/](https://ladybugdb.com/)) or (RuyGraph)[https://www.ryugraph.io/] database as a graph in a Jupyter Notebook. 

This packages provides an easy-to-use interface to
the [yFiles Graphs for Jupyter](https://github.com/yWorks/yfiles-jupyter-graphs) widget to directly visualize Cypher
queries.

## Installation
Just install it from the [Python Package Index](https://pypi.org/project/yfiles-jupyter-graphs-for-kuzu/)
```bash
pip install yfiles_jupyter_graphs_for_kuzu
```
or see [README_DEV.md](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/README_DEV.md) to build it yourself.

## Usage

```python
# unquote the graphdb module you use
# import real_ladybug
# import ryugraph

from yfiles_jupyter_graphs_for_kuzu import KuzuGraphWidget

db_path = '<path-to-db>'

if "real_ladybug" in sys.modules:
    db: real_ladybug.Database = real_ladybug.Database(db_path)
    conn: real_ladybug.Connection = real_ladybug.Connection(db)
else:
    db: ryugraph.Database = ryugraph.Database(db_path)
    conn: ryugraph.Connection = ryugraph.Connection(db)

g = KuzuGraphWidget(conn)

g.show_cypher("MATCH (s)-[r]->(t) RETURN s,r,t LIMIT 20")
```

See
the [basic example notebook](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/introduction.ipynb) for a running example.
Also see [legacy Kuzu introduction example](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/introduction.ipynb).

## Supported Environments

The widget uses yFiles Graphs for Jupyter at its core, and therefore runs in any environment that is supported by it,
see [supported environments](https://github.com/yWorks/yfiles-jupyter-graphs/tree/main?tab=readme-ov-file#supported-environments).

## Documentation

The main class `KuzuGraphWidget` provides the following API:

### Constructor

- `KuzuGraphWidget`: Creates a new class instance with the following arguments

| Argument           | Description                                                                                                                                                                                                                                 | Default   |
|--------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------|
| `driver`           | The Kuzu `driver` that is used to execute Cypher queries.                                                                                                                                                                                   | `None`    |
| `widget_layout`    | Can be used to specify general widget appearance through css attributes. See ipywidget's [`layout`](https://ipywidgets.readthedocs.io/en/stable/examples/Widget%20Layout.html#the-layout-attribute) for more information.                   | `None`    |
| `overview_enabled` | Enable graph overview component. Default behaviour depends on cell width.                                                                                                                                                                   | `None`    |
| `context_start_with` | Start with a specific side-panel opened in the interactive widget. Starts with closed side-panel by default.                                                                                                                                | `None`    |
| `layout`     | Can be used to specify a general default node and edge layout. Available algorithms are: "circular", "hierarchic", "organic", "interactive_organic", "orthogonal", "radial", "tree", "map", "orthogonal_edge_router", "organic_edge_router" | `organic` |

### Methods 

- `show_cypher(cypher: str, layout: Optional[str] = None, **kwargs: Dict[str, Any]) -> None`
    - `cypher (str)`: The [Cypher query](https://neo4j.com/docs/cypher-manual/current/introduction/) that should be
      visualized.
    - `layout (Optional[str])`: The graph layout that is used. This overwrites the general layout in this specific graph instance. The following arguments are supported:
        - `hierarchic`
        - `organic`
        - `interactive_organic`
        - `circular`
        - `circular_straight_line`
        - `orthogonal`
        - `tree`
        - `radial`
        - `map`
        - `orthogonal_edge_router`
        - `organic_edge_router`
    - `**kwargs (Dict[str, Any])`: Additional parameters that should be passed to the Cypher query.

The default behavior is to only show the nodes and relationships returned by the Cypher query.

The Cypher queries are executed by the provided Kuzu driver. If you have not specified a driver when instantiating the
class, you can set
a connection afterward:

- `set_connection(driver)`: Sets the Kuzu driver that is used to resolve the Cypher queries.
- `get_connection()`: Returns the current Kuzu driver.

The graph visualization can be adjusted by adding configurations to each node label or edge type with the following
functions:

- `add_node_configuration(label: Union[str, list[str]], **kwargs: Dict[str, Any]) -> None`
    - `label (Union[str, list[str]])`: The node label(s) for which this configuration should be used. Supports `*` to address all labels.
    - `**kwargs (Dict[str, Any])`: Visualization configuration for the given node label. The following arguments are supported:
        - `text`: The text that displayed at the node. By default, the node's label is used.
        - `color`: A convenience color binding for the node (see also `styles` argument).
        - `size`: The size of the node.
        - `styles`: A dictionary that may contain the following attributes `color`, `shape` (one of 'ellipse', '
          hexagon', 'hexagon2', 'octagon', 'pill', 'rectangle', 'round-rectangle' or 'triangle'), `image`.
        - `property`: Allows to specify additional properties on the node, which may be bound by other bindings.
        - `type`: Defines a specific "type" for the node as described
          in [yFiles Graphs for Jupyter](https://yworks.github.io/yfiles-jupyter-graphs/02_graph_widget/#def-default_node_type_mappingindex-node)
          which affects the automatic positioning of nodes (same "type"s are preferred to be placed next to each other).
        - `parent_configuration`: Configure grouping for this node label. See [features.ipynb](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb)
          for examples.

- `add_relationship_configuration(type: Union[str, list[str]], **kwargs: Dict[str, Any]) -> None`
    - `type (Union[str, list[str]])`: The relationship type for which this configuration should be used. Supports `*` to address all types.
    - `**kwargs`: Visualization configuration for the given relationship type. The following arguments are supported:
        - `text`: The text that displayed at the relationship. By default, the relationship's type is used.
        - `color`: The relationship's color.
        - `thickness_factor`: The relationship's stroke thickness factor. By default, `1`.
        - `styles`: The style of the edge.
        - `property`: Allows to specify additional properties on the relationship, which may be bound by other bindings.

- `add_parent_relationship_configuration(type: Union[str, list[str]], reverse: Optional[bool] = False) -> None`
    - `type`: The relationship type that should be visualized as node grouping hierarchy instead of the actual relationship.
    - `reverse`: By default the target node is considered as parent. This can be reverted with this argument.

To remove a configuration use the following functions: 

- `del_node_configuration(label: Union[str, list[str]]) -> None`: Deletes configuration for the given node label(s). Supports `*` to address all types.
- `del_relationship_configurations(type: Union[str, list[str]]) -> None`: Deletes configuration for the given relationship type(s). Supports `*` to address all labels.
- `del_parent_relationship_configuration(type: Union[str, list[str]]) -> None`: Deletes configuration for the given parent relationship type(s).

## How configuration bindings are resolved

The configuration bindings (see `add_node_configuration` or `add_relationship_configuration`) are resolved as follows:

If the configuration binding is a string, the package first tries to resolve it against the item's properties
and uses the property value if available. If there is no property with the given key, the string value itself is used as
a constant binding.

In case you want to create a constant string value as binding, which also happens to be a property key, use a binding
function with a constant string as return value instead.

If the configuration binding is a function, the return value of the function is used as value for the respective
configuration.

## yFiles Graphs for Jupyter

The graph visualization is provided by [yFiles Graphs for Jupyter](https://github.com/yWorks/yfiles-jupyter-graphs), a
versatile graph visualization widget for Jupyter Notebooks.

It can import and visualize graphs from various popular Python packages
(e.g. [NetworkX](https://github.com/yWorks/yfiles-jupyter-graphs/blob/main/examples/13_networkx_import.ipynb), 
[PyGraphviz](https://github.com/yWorks/yfiles-jupyter-graphs/blob/main/examples/15_graphviz_import.ipynb),
[igraph](https://github.com/yWorks/yfiles-jupyter-graphs/blob/main/examples/17_igraph_import.ipynb)) or just structured
[node and edge lists](https://github.com/yWorks/yfiles-jupyter-graphs/blob/main/examples/01_introduction.ipynb).

And provides a rich set of visualization options to bring your data to life (see
the [example notebooks](https://github.com/yWorks/yfiles-jupyter-graphs/blob/main/examples/00_toc.ipynb)).

### Feature Highlights

<table>
    <tr>
        <td><a href="https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb"><img src="https://raw.githubusercontent.com/yWorks/yfiles-jupyter-graphs-for-kuzu/refs/heads/main/images/features/heat_feature.png" title="Heatmap visualization" alt="Heatmap visualization"></a>
        <a href="https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb">Heatmap visualization</a><br><a target="_blank" href="https://colab.research.google.com/github/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a></td>
        <td><img src="https://raw.githubusercontent.com/yWorks/yfiles-jupyter-graphs-for-kuzu/refs/heads/main/images/features/map_feature.png" title="Geospatial data visualization" alt="Geospatial data visualization">Geospatial data visualization</td>
    </tr>
    <tr>
        <td><a href="https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb"><img src="https://raw.githubusercontent.com/yWorks/yfiles-jupyter-graphs-for-kuzu/refs/heads/main/images/features/size_feature.png" title="Data-driven item visualization" alt="Data-driven item visualization"></a>
        <a href="https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb">Data-driven item visualization</a><br><a target="_blank" href="https://colab.research.google.com/github/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a></td>
        <td><a href="https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb"><img src="https://raw.githubusercontent.com/yWorks/yfiles-jupyter-graphs-for-kuzu/refs/heads/main/images/features/grouping_feature.png" title="Grouped items" alt="node nesting"></a>
        <a href="https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb">Group items</a><br><a target="_blank" href="https://colab.research.google.com/github/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/examples/features.ipynb"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a></td>
    </tr>
</table>

For a detailed feature guide, check out the main widget [example notebooks](https://colab.research.google.com/github/yWorks/yfiles-jupyter-graphs/blob/main/examples/00_toc.ipynb)

## Code of Conduct

This project and everyone participating in it is governed by
the [Code of Conduct](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/CODE_OF_CONDUCT.md).
By participating, you are expected to uphold this code.
Please report unacceptable behavior to [contact@yworks.com](mailto:contact@yworks.com).

## Feedback

This widget is by no means perfect.
If you find something is not working as expected
we are glad to receive an issue report from you.
Please make sure
to [search for existing issues](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/search?q=is%3Aissue) first
and check if the issue is not an unsupported feature or known issue.
If you did not find anything related, report a new issue with necessary information.
Please also provide a clear and descriptive title and stick to the issue templates.
See [issues](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/issues).

## Dependencies

* [yFiles Graphs for Jupyter](https://github.com/yWorks/yfiles-jupyter-graphs)

## License
See [LICENSE](https://github.com/yWorks/yfiles-jupyter-graphs-for-kuzu/blob/kuzu/LICENSE.md) file.
