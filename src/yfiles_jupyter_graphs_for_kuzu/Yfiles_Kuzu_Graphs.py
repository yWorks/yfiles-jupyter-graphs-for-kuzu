"""Jupyter (ipy)widget powered by yFiles.

The main KuzuGraphWidget class is defined in this module.

"""
from typing import Any, Callable, Dict, Union, Optional, List, Tuple
import inspect
from datetime import date, datetime
import warnings

from yfiles_jupyter_graphs import GraphWidget

# TODO maybe change to get dynamically when adding bindings

POSSIBLE_NODE_BINDINGS = {'coordinate', 'color', 'size', 'type', 'styles', 'scale_factor', 'position',
                          'layout', 'property', 'label'}
POSSIBLE_EDGE_BINDINGS = {'color', 'thickness_factor', 'styles', 'property', 'label'}
COLOR_PALETTE = ['#2196F3', '#4CAF50', '#F44336', '#607D8B', '#673AB7', '#CDDC39', '#9E9E9E', '#9C27B0']
KUZU_LABEL_KEYS = ['name', 'title', 'text', 'description', 'caption', 'label']

class KuzuGraphWidget:
    """
    A yFiles Graphs for Jupyter widget that is tailored to visualize Cypher queries resolved against a Kuzu database.
    """

    # noinspection PyShadowingBuiltins
    def __init__(self, connection: Optional[Any] = None, widget_layout: Optional[Any] = None,
                 overview_enabled: Optional[bool] = None, context_start_with: Optional[str] = None,
                 license: Optional[Dict] = None, layout: Optional[str] = 'organic'):
        """
        Initializes a new instance of the KuzuGraphWidget class.

        Args:
            connection (Optional[kuzu connection type]): The Kuzu connection to resolve the Cypher queries.
            widget_layout (Optional[ipywidgets.Layout]): Can be used to specify general widget appearance through css attributes.
                See ipywidgets documentation for the available keywords.
            overview_enabled (Optional[bool]): Whether the graph overview is enabled or not.
            context_start_with (Optional[str]): Start with a specific side-panel opened in the interactive widget. Starts with closed side-panel by default.
            license (Optional[Dict]): The widget works on common public domains without a specific license.
                For unknown domains, a license can be obtained by the creators of the widget.
            layout (Optional[str]): Specifies the default automatic graph arrangement. Can be overwritten for each
                cypher separately. By default, an "organic" layout is used. Supported values are:
                    - "circular"
                    - "circular_straight_line"
                    - "hierarchic"
                    - "organic"
                    - "interactive_organic"
                    - "orthogonal"
                    - "radial"
                    - "tree"
                    - "map"
                    - "orthogonal_edge_router"
                    - "organic_edge_router"
        """

        self._widget = None
        self._connection = connection
        self._license = license
        self._overview = overview_enabled
        self._layout = widget_layout
        self._context_start_with = context_start_with
        self._graph_layout = layout

        self._node_configurations = {}
        self._edge_configurations = {}
        self._parent_configurations = set()

        # a mapping of node/edge types to a color, e.g. item types are automatically mapped to
        # different colors
        self._itemtype2colorIdx = {}

    def set_connection(self, connection: Any) -> None:
        """
        The Kuzu connection that is used to resolve the Cypher queries. A new session is created when set.

        Args:
            connection: The Kuzu connection to resolve the Cypher queries.

        Returns:
            None
        """
        warnings.warn(
            "set_connection() is deprecated. Use the 'connection' property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.connection = connection

    def get_connection(self) -> Any:
        """
        Gets the configured Kuzu connection.

        Returns:
            kuzu connection
        """
        warnings.warn(
            "get_connection() is deprecated. Use the 'connection' property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.connection

    @property
    def connection(self) -> Any:
        """The configured Kuzu connection.

        Preferred Pythonic accessor to the underlying connection. Equivalent to get_connection().
        """
        return self._connection

    @connection.setter
    def connection(self, value: Any) -> None:
        """Sets the Kuzu connection used to resolve Cypher queries."""
        self._connection = value

    @property
    def graph_widget(self) -> Optional[GraphWidget]:
        """
        Returns the most recent GraphWidget created by show_cypher(), or None if show_cypher() has not been called yet.
        """
        return self._widget

    def _parse_query_result(self, query_result: Any) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse a Kuzu graph database query result DataFrame into nodes and relationships.

        Args:
            query_result: QueryResult generator from Kuzu that contains a list of query results
            with node and relationship columns

        Returns:
            Tuple containing (nodes, relationships) as lists of dictionaries
        """
        # Helper functions
        def encode_node_id(node: dict[str, Any], table_primary_key_dict: dict[str, Any]) -> str:
            node_label = node["_label"]
            return f"{node_label}_{node[table_primary_key_dict[node_label]]!s}"

        def encode_rel_id(rel: dict[str, Any]) -> tuple[int, int]:
            return rel["_id"]["table"], rel["_id"]["offset"]

        def clean_value(v: Any) -> Any:
            if isinstance(v, (date, datetime)):
                return v.isoformat()
            return v

        if self._connection is None:
            raise ValueError("No database connection provided. Initialize widget with a valid Kuzu connection.")

        result = []
        while query_result.has_next():  # type: ignore
            result.append(query_result.get_next())  # type: ignore

        node_map = {}
        relationship_map = {}
        table_to_label_dict = {}
        table_primary_key_dict = {}

        # Process each row in the result
        for row in result:
            # Each row is a list with values for s,r,t in order
            for value in row:
                # Skip empty values
                if value is None or value == {}:
                    continue

                # Process nodes
                if "_label" in value and "_id" in value and not ("_src" in value and "_dst" in value):
                    self._process_node(value, node_map, table_to_label_dict)

                # Process relationships
                elif "_label" in value and "_src" in value and "_dst" in value:
                    # Remove None values from the relationship
                    self._remove_none_values(value)
                    relationship_map[encode_rel_id(value)] = value

                # Process recursive relationships and their associated nodes
                elif "_nodes" in value and "_rels" in value:
                    recursive_nodes = value["_nodes"]
                    for node in recursive_nodes:
                        self._process_node(node, node_map, table_to_label_dict)

                    recursive_rels = value["_rels"]
                    for rel in recursive_rels:
                        # Remove None values from the relationship
                        self._remove_none_values(rel)
                        relationship_map[encode_rel_id(rel)] = rel

        # Convert nodes to the result format
        result_nodes = []
        for node in node_map.values():
            node_label = node["_label"]
            # Get primary key for each node label using table info
            node_tbl_info = self._connection.execute(f"CALL TABLE_INFO('{node_label}') RETURN *")
            node_tbl_properties = []
            while node_tbl_info.has_next():  # type: ignore
                prop = node_tbl_info.get_next()  # type: ignore
                if prop[-1] is True:
                    # Kuzu enforces that every node table MUST have one and only one primary key, so
                    # this `if` condition is guaranteed to be hit in all scenarios
                    table_primary_key_dict[node_label] = prop[1]
                    node_tbl_properties.append(prop[1])
                    break

            # Store the node results
            node_id = encode_node_id(node, table_primary_key_dict)
            while node_tbl_info.has_next():  # type: ignore
                prop = node_tbl_info.get_next()  # type: ignore
                # Add all the remaining properties to the node table list
                node_tbl_properties.append(prop[1])
            result_nodes.append({
                "id": node_id,
                "properties": {
                    "label": node["_label"],
                    **{k: clean_value(v) for k, v in node.items() if not k.startswith('_') and k in node_tbl_properties}
                }
            })

        # Convert relationships to the result format
        result_relationships = []
        for rel in relationship_map.values():
            _src = rel["_src"]
            _dst = rel["_dst"]
            src_node = node_map[(_src["table"], _src["offset"])]
            dst_node = node_map[(_dst["table"], _dst["offset"])]
            src_id = encode_node_id(src_node, table_primary_key_dict)
            dst_id = encode_node_id(dst_node, table_primary_key_dict)

            rel_tbl_info = self._connection.execute(f"CALL TABLE_INFO('{rel['_label']}') RETURN *")
            rel_tbl_properties = []
            while rel_tbl_info.has_next():  # type: ignore
                prop = rel_tbl_info.get_next()  # type: ignore
                rel_tbl_properties.append(prop[1])

            _, offset = encode_rel_id(rel)   # The first value is the table id & isn't needed
            rel_id = f"{src_node['_label']}_{dst_node['_label']}_{offset}"
            result_relationships.append({
                "id": rel_id,
                "start": src_id,
                "end": dst_id,
                "properties": {
                    "label": rel["_label"],
                    **{k: clean_value(v) for k, v in rel.items() if not k.startswith('_') and k in rel_tbl_properties}
                }
            })

        return result_nodes, result_relationships

    def _process_node(self,
            node: Dict[str, Any],
            node_map: Dict[Tuple[int, int], Dict[str, Any]], 
            table_to_label_dict: Dict[int, str]
        ) -> None:
        """
        Update the node map and table-to-label dict.
        
        Args:
            node: The node to process
            node_map: The map to store nodes in
            table_to_label_dict: The dict mapping table IDs to labels
        """
        _id = node["_id"]
        node_map[(_id["table"], _id["offset"])] = node
        table_to_label_dict[_id["table"]] = node["_label"]
        
    def _remove_none_values(self, dictionary: Dict[str, Any]) -> None:
        """
        Remove a `None` key's values from a dict.
        
        Args:
            dict: The dict whose None keys need cleaning
        """
        for key in list(dictionary.keys()):
            if dictionary[key] is None:
                del dictionary[key]

    def _default_color_mapping(self, element: Dict):
        itemtype = element['properties']['label']
        if itemtype not in self._itemtype2colorIdx:
            self._itemtype2colorIdx[itemtype] = len(self._itemtype2colorIdx)

        color_index = self._itemtype2colorIdx[itemtype] % len(COLOR_PALETTE)
        return COLOR_PALETTE[color_index]

    def show_cypher(self, cypher: str, layout: Optional[str] = None, **kwargs: Dict[str, Any]) -> None:
        """
        Displays the given Cypher query as interactive graph.

        Args:
            cypher (str): The Cypher query whose result should be visualized as graph.
            layout (Optional[str]): The graph layout for this request. Overwrites the general default `layout` that was
                specified when initializing the class. Supported values are:
                    - "circular"
                    - "circular_straight_line"
                    - "hierarchic"
                    - "organic"
                    - "interactive_organic"
                    - "orthogonal"
                    - "radial"
                    - "tree"
                    - "map"
                    - "orthogonal_edge_router"
                    - "organic_edge_router"
            **kwargs (Dict[str, Any]): Additional parameters that should be passed to the Cypher query.

        Returns:
            None

        Raises:
            Exception: If no driver was specified.
        """
        if self._connection is not None:
            widget = GraphWidget(overview_enabled=self._overview, context_start_with=self._context_start_with,
                                 widget_layout=self._layout, license=self._license)

            # show directedness of relationships by default
            widget.directed = True

            query_result = self._connection.execute(cypher, **kwargs)
            nodes, edges = self._parse_query_result(query_result)
            widget.nodes = nodes
            widget.edges = edges

            self.__create_group_nodes(self._node_configurations, widget)
            self.__apply_node_mappings(widget)
            self.__apply_edge_mappings(widget)
            self.__apply_heat_mapping({**self._node_configurations, **self._edge_configurations}, widget)
            self.__apply_parent_mapping(widget)
            if layout is None:
                widget.set_graph_layout(self._graph_layout)
            else:
                widget.set_graph_layout(layout)

            widget.node_cell_mapping = self.node_cell_mapping

            self._widget = widget
            widget.show()
        else:
            raise Exception("no driver specified")

    @staticmethod
    def __get_item_text(element: Dict) -> Union[str, None]:
        lowercase_element_props = {key.lower(): value for key, value in element.get('properties', {}).items()}
        for key in KUZU_LABEL_KEYS:
            if key in lowercase_element_props:
                return str(lowercase_element_props[key])
        return None

    @staticmethod
    def __configuration_mapper_factory(binding_key: str, configurations: Dict[str, Dict[str, str]],
                                       default_mapping: Callable) -> Callable[[int, Dict], Union[Dict, str]]:
        """
        This is called once for each POSSIBLE_NODE_BINDINGS or POSSIBLE_EDGE_BINDINGS (as `binding_key` argument) and
        sets the returned mapping function for the `binding_key` on the core yFiles Graphs for Jupyter widget.

        Args:
            binding_key (str): One of POSSIBLE_NODE_BINDINGS or POSSIBLE_EDGE_BINDINGS
            configurations (Dict): All configured node or relationship configurations by the user, keyed by the node label or relationship type.
                For example, a dictionary built like:
                {
                  "Movie": { "color": "red", ... },
                  "Person": { "color": "blue", ... },
                  "*": { "color": "gray", ... }
                }
            default_mapping (MethodType): A reference to the default binding of the yFiles Graphs for Jupyter core widget that should be used when the binding_key is not specified otherwise.

        Returns:
            FunctionType: A mapping function that can used in the yFiles Graphs for Jupyter core widget.
        """

        def mapping(index: int, item: Dict) -> Union[Dict, str]:
            label = item["properties"]["label"]  # yjg stores the kuzu node/relationship type in properties["label"]
            if ((label in configurations or '*' in configurations)
                    and binding_key in configurations.get(label, configurations.get('*'))):
                type_configuration = configurations.get(label, configurations.get('*'))
                if binding_key == 'parent_configuration':
                    # the binding may be a lambda that must be resolved first
                    binding = type_configuration.get(binding_key)
                    if callable(binding):
                        binding = binding(item)
                    # parent_configuration binding may either resolve to a dict or a string
                    if isinstance(binding, dict):
                        group_label = binding.get('text', '')
                    else:
                        group_label = binding
                    result = 'GroupNode' + group_label
                # mapping
                elif callable(type_configuration[binding_key]):
                    result = type_configuration[binding_key](item)
                # property name
                elif (not isinstance(type_configuration[binding_key], dict) and
                      type_configuration[binding_key] in item["properties"]):
                    result = item["properties"][type_configuration.get(binding_key)]
                # constant value
                else:
                    result = type_configuration.get(binding_key)

                return result

            if binding_key == "label":
                return KuzuGraphWidget.__get_item_text(item)
            else:
                # call default mapping
                # some default mappings do not support "index" as first parameter
                parameters = inspect.signature(default_mapping).parameters
                if len(parameters) > 1 and parameters[list(parameters)[0]].annotation == int:
                    return default_mapping(index, item)
                else:
                    return default_mapping(item)

        return mapping

    def __apply_heat_mapping(self, configuration, widget: GraphWidget) -> None:
        setattr(widget, "_heat_mapping",
                KuzuGraphWidget.__configuration_mapper_factory('heat', configuration,
                                                                getattr(widget, 'default_heat_mapping')))

    def __create_group_nodes(self, configurations, widget: GraphWidget) -> None:
        group_node_properties = set()
        group_node_values = set()
        key = 'parent_configuration'
        for node in widget.nodes:
            label = node['properties']['label']
            if label in configurations and key in configurations.get(label):
                group_node = configurations.get(label).get(key)

                if callable(group_node):
                    group_node = group_node(node)

                if isinstance(group_node, str):
                    # string or property value
                    if group_node in node["properties"]:
                        group_node_properties.add(str(node["properties"][group_node]))
                    else:
                        group_node_values.add(group_node)
                else:
                    # dictionary with values
                    text = group_node.get('text', '')
                    group_node_values.add(text)
                    configuration = {k: v for k, v in group_node.items() if k != 'text'}
                    self.add_node_configuration(text, **configuration)

        for group_label in group_node_properties.union(group_node_values):
            node = {'id': 'GroupNode' + group_label, 'properties': {'label': group_label}}
            widget.nodes = [*widget.nodes, node]

    def __apply_parent_mapping(self, widget: GraphWidget) -> None:
        node_to_parent = {}
        edge_ids_to_remove = set()
        for edge in widget.edges[:]:
            rel_type = edge["properties"]["label"]
            for (parent_type, is_reversed) in self._parent_configurations:
                if rel_type == parent_type:
                    start = edge['start']  # child node id
                    end = edge['end']  # parent node id
                    if is_reversed:
                        node_to_parent[end] = start
                    else:
                        node_to_parent[start] = end
                    edge_ids_to_remove.add(edge['id'])
                    break

        # use list comprehension to filter out the edges to automatically trigger model sync with the frontend
        widget.edges = [edge for edge in widget.edges if edge['id'] not in edge_ids_to_remove]
        current_parent_mapping = getattr(widget, '_node_parent_mapping')
        setattr(widget, "_node_parent_mapping",
                lambda index, node: node_to_parent.get(node['id'], current_parent_mapping(index, node)))

    def __apply_node_mappings(self, widget: GraphWidget) -> None:
        for key in POSSIBLE_NODE_BINDINGS:
            default_mapping = self._default_color_mapping if key == "color" else getattr(widget, f"default_node_{key}_mapping")
            setattr(widget, f"_node_{key}_mapping",
                    KuzuGraphWidget.__configuration_mapper_factory(key, self._node_configurations, default_mapping))
        # manually set parent configuration
        setattr(widget, f"_node_parent_mapping",
                KuzuGraphWidget.__configuration_mapper_factory('parent_configuration',
                                                                self._node_configurations, lambda node: None))

    def __apply_edge_mappings(self, widget: GraphWidget) -> None:
        for key in POSSIBLE_EDGE_BINDINGS:
            default_mapping = self._default_color_mapping if key == "color" else getattr(widget, f"default_edge_{key}_mapping")
            setattr(widget, f"_edge_{key}_mapping",
                    KuzuGraphWidget.__configuration_mapper_factory(key, self._edge_configurations, default_mapping))

    def add_node_configuration(self, label: Union[str, list[str]], **kwargs: Dict[str, Any]) -> None:
        """
        Adds a configuration object for the given node `label`(s).

        Args:
            label (Union[str, list[str]]): The node label(s) for which this configuration should be used. Supports `*` to address all labels.
            **kwargs (Dict[str, Any]): Visualization configuration for the given node label. The following arguments are supported:

                - `text` (Union[str, Callable]): The text to be displayed on the node. By default, the node's label is used.
                - `color` (Union[str, Callable]): A convenience color binding for the node (see also styles kwarg).
                - `size` (Union[str, Callable]): The size of the node.
                - `styles` (Union[Dict, Callable]): A dictionary that may contain the following attributes color, shape (one of 'ellipse', ' hexagon', 'hexagon2', 'octagon', 'pill', 'rectangle', 'round-rectangle' or 'triangle'), image.
                - `property` (Union[Dict, Callable]): Allows to specify additional properties on the node, which may be bound by other bindings.
                - `type` (Union[Dict, Callable]): Defines a specific "type" for the node which affects the automatic positioning of nodes (same "type"s are preferred to be placed next to each other).
                - `parent_configuration` (Union[str, Callable]): Configure grouping for this node label.

        Returns:
            None
        """
        # this wrapper uses "text" as text binding in the graph
        # in contrast to "label" which is used in yfiles-jupyter-graphs
        text_binding = kwargs.pop("text", None)
        config = kwargs
        if text_binding is not None:
            config["label"] = text_binding

        cloned_config = {key: value for key, value in config.items()}
        if isinstance(label, list):
            for l in label:
                self._node_configurations[l] = cloned_config
        else:
            self._node_configurations[label] = cloned_config

    # noinspection PyShadowingBuiltins
    def add_relationship_configuration(self, type: Union[str, list[str]], **kwargs: Dict[str, Any]) -> None:
        """
        Adds a configuration object for the given relationship `type`(s).

        Args:
            type (Union[str, list[str]]): The relationship type(s) for which this configuration should be used. Supports `*` to address all labels.
            **kwargs (Dict): Visualization configuration for the given node label. The following arguments are supported:

                - `text` (Union[str, Callable]): The text to be displayed on the node.  By default, the relationship's type is used.
                - `color` (Union[str, Callable]): The relationship's color.
                - `thickness_factor` (Union[str, Callable]): The relationship's stroke thickness factor. By default, 1.
                - `property` (Union[Dict, Callable]): Allows to specify additional properties on the relationship, which may be bound by other bindings.

        Returns:
            None
        """
        # this wrapper uses "text" as text binding in the graph
        # in contrast to "label" which is used in yfiles-jupyter-graphs
        text_binding = kwargs.pop("text", None)
        config = kwargs
        if text_binding is not None:
            config["label"] = text_binding

        cloned_config = {key: value for key, value in config.items()}
        if isinstance(type, list):
            for t in type:
                self._edge_configurations[t] = cloned_config
        else:
            self._edge_configurations[type] = cloned_config

    # noinspection PyShadowingBuiltins
    def add_parent_relationship_configuration(self, type: Union[str, list[str]], reverse: Optional[bool] = False) -> None:
        """
        Configure specific relationship types to visualize as nested hierarchies. This removes these relationships from
        the graph and instead groups the related nodes (source and target) as parent-child.

        Args:
            type (Union[str, list[str]]): The relationship type(s) that should be visualized as node grouping hierarchy instead of the actual relationship.
            reverse (bool): Which node should be considered as parent. By default, the target node is considered as parent which can be reverted with this argument.

        Returns:
            None
        """
        if isinstance(type, list):
            for t in type:
                self._parent_configurations.add((t, reverse))
        else:
            self._parent_configurations.add((type, reverse))

    # noinspection PyShadowingBuiltins
    def del_node_configuration(self, label: Union[str, list[str]]) -> None:
        """
        Deletes the configuration object for the given node `label`(s).

        Args:
            label (Union[str, list[str]]): The node label(s) for which the configuration should be deleted. Supports `*` to address all labels.

        Returns:
            None
        """
        if isinstance(label, list):
            for l in label:
                KuzuGraphWidget.__safe_delete_configuration(l, self._node_configurations)
        else:
            KuzuGraphWidget.__safe_delete_configuration(label, self._node_configurations)

    # noinspection PyShadowingBuiltins
    def del_relationship_configuration(self, type: Union[str, list[str]]) -> None:
        """
        Deletes the configuration object for the given relationship `type`(s).

        Args:
            type (Union[str, list[str]]): The relationship type(s) for which the configuration should be deleted. Supports `*` to address all types.

        Returns:
            None
        """
        if isinstance(type, list):
            for t in type:
                KuzuGraphWidget.__safe_delete_configuration(t, self._edge_configurations)
        else:
            KuzuGraphWidget.__safe_delete_configuration(type, self._edge_configurations)

    @staticmethod
    def __safe_delete_configuration(key: str, configurations: Dict[str, Any]) -> None:
        if key == "*":
            configurations.clear()
        if key in configurations:
            del configurations[key]

    # noinspection PyShadowingBuiltins
    def del_parent_relationship_configuration(self, type: Union[str, list[str]]) -> None:
        """
        Deletes the relationship configuration for the given `type`(s).

        Args:
            type (Union[str, list[str]]): The relationship type(s) for which the configuration should be deleted.

        Returns:
            None
        """
        if isinstance(type, list):
            self._parent_configurations = {
                rel_type for rel_type in self._parent_configurations if rel_type[0] not in type
            }
        else:
            self._parent_configurations = {
                rel_type for rel_type in self._parent_configurations if rel_type[0] != type
            }

    @property
    def node_cell_mapping(self) -> Union[str, Callable, None]:
        """
        The currently specified node cell mapping.

        This mapping is used by automatic layout algorithms. It should resolve to a
        (row, column) tuple or be a callable that returns such a tuple for a node.
        """
        return self._node_cell_mapping if hasattr(self, '_node_cell_mapping') else None

    @node_cell_mapping.setter
    def node_cell_mapping(self, node_cell_mapping: Union[str, Callable]) -> None:
        """Specify or update the node-to-cell mapping used by automatic layouts."""
        # noinspection PyAttributeOutsideInit
        self._node_cell_mapping = node_cell_mapping

    @node_cell_mapping.deleter
    def node_cell_mapping(self) -> None:  # type: ignore[override]
        """Delete the node-to-cell mapping if present."""
        if hasattr(self, '_node_cell_mapping'):
            delattr(self, '_node_cell_mapping')

    # Backwards-compatible wrappers (deprecated)
    def get_node_cell_mapping(self) -> Union[str, Callable, None]:
        """
        Deprecated: Use the 'node_cell_mapping' property instead.
        """
        warnings.warn(
            "get_node_cell_mapping() is deprecated. Use the 'node_cell_mapping' property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.node_cell_mapping

    def set_node_cell_mapping(self, node_cell_mapping: Union[str, Callable]) -> None:
        """
        Deprecated: Use the 'node_cell_mapping' property instead.
        """
        warnings.warn(
            "set_node_cell_mapping() is deprecated. Use the 'node_cell_mapping' property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.node_cell_mapping = node_cell_mapping

    def del_node_cell_mapping(self) -> None:
        """
        Deprecated: Use the 'node_cell_mapping' property instead.
        """
        warnings.warn(
            "del_node_cell_mapping() is deprecated. Use the 'node_cell_mapping' property instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            del self.node_cell_mapping
        except AttributeError:
            pass