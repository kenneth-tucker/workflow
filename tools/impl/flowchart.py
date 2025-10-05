import graphviz
from tools.impl.experiment_model import ExperimentModel

class FlowChart:
    """
    Converts an experiment model into a flowchart visualization
    using Graphviz.
    """

    # Color constants for easy customization
    COLOR_NODE_DEFAULT = "lightgrey"
    COLOR_NODE_ACTIVE = "orange"
    COLOR_NODE_ACTIVE_FLOW = "#b35900"
    COLOR_NODE_BEGIN_DEFAULT = "#d6e4ec"
    COLOR_NODE_BEGIN_ACTIVE = "#b35900"
    COLOR_NODE_END_DEFAULT = "#d6e4ec"
    COLOR_NODE_END_ACTIVE = "#b35900"
    COLOR_EDGE_DEFAULT = "lightgrey"
    COLOR_EDGE_ACTIVE = "orange"

    # Number of recent path edges to highlight
    NUM_PATH_EDGES_TO_HIGHLIGHT = 2

    def __init__(self, experiment_model: ExperimentModel):
        self.experiment_model = experiment_model
        self.graph = graphviz.Digraph(
            format="png",
            node_attr={"shape": "box", "style": "rounded,filled", "fillcolor": self.COLOR_NODE_DEFAULT},
            edge_attr={"color": self.COLOR_EDGE_DEFAULT},
        )
        with self.graph.subgraph(name=experiment_model.experiment_name) as subgraph:
            self._populate_subgraph("", subgraph)

    def save_as_png(self, path: str):
        """
        Render the flowchart to a PNG file.
        """
        self.graph.render(
            path,
            cleanup=True,
            format="png",
            engine="dot"
        )

    # Private helper methods for building the graph

    def _populate_subgraph(self, flow_full_name: str, subgraph: graphviz.Digraph):
        """
        Orchestrate the population of a subgraph for a given flow.
        Adds the begin node, part nodes, edges, and ending nodes/edges.
        """
        begin_node, first_part_full = self._add_begin_node(flow_full_name, subgraph)
        active_flow = self.experiment_model.flow_stack[-1] if self.experiment_model.flow_stack else ""
        self._add_part_nodes(flow_full_name, subgraph, active_flow)
        path_edges_to_highlight = self._collect_path_edges_to_highlight(flow_full_name, begin_node)
        self._add_edges_and_endings(
            flow_full_name, subgraph, path_edges_to_highlight, begin_node, first_part_full
        )

    def _add_begin_node(self, flow_full_name: str, subgraph: graphviz.Digraph) -> tuple[str | None, str | None]:
        """
        Add the 'begin' node and return its name and the first part's full name if applicable.
        """
        # Get first_part from the experiment model's flow_first_parts
        first_part = self.experiment_model.flow_first_parts.get(flow_full_name, None)
        begin_node = None
        if first_part:
            # Highlight the begin node if this flow is active
            active_flow = self.experiment_model.flow_stack[-1] if self.experiment_model.flow_stack else ""
            color = self.COLOR_NODE_BEGIN_ACTIVE if flow_full_name == active_flow else self.COLOR_NODE_BEGIN_DEFAULT                
            begin_node = f"begin_{flow_full_name}" if flow_full_name else "begin"
            subgraph.node(begin_node, label="start", shape="circle", style="filled", fillcolor=color)
        return begin_node, first_part

    def _add_part_nodes(self, flow_full_name: str, subgraph: graphviz.Digraph, active_flow: str) -> None:
        """
        Add nodes for all parts in the current flow (flow, decision, step), with appropriate coloring.
        """
        for part_full_name, part_model in self.experiment_model.experiment_parts.items():
            if self._is_child(part_full_name, flow_full_name):
                if part_model.part_category == "flow":
                    # Create a subgraph for the nested flow, color if the active flow or active part
                    if self.experiment_model.part_path and \
                       part_model.full_name == self.experiment_model.part_path[-1]:
                        subgraph.node(part_model.full_name, shape="component", fillcolor=self.COLOR_NODE_ACTIVE)
                    elif active_flow and part_model.full_name == active_flow:
                        subgraph.node(part_model.full_name, shape="component", fillcolor=self.COLOR_NODE_ACTIVE_FLOW)
                    else:
                        subgraph.node(part_model.full_name, shape="component", fillcolor=self.COLOR_NODE_DEFAULT)
                    with subgraph.subgraph(name=part_model.full_name) as child_subgraph:
                        self._populate_subgraph(part_model.full_name, child_subgraph)
                elif part_model.part_category == "decision":
                    # Decision parts as diamonds, color if it is the active part
                    if self.experiment_model.part_path and \
                       part_model.full_name == self.experiment_model.part_path[-1]:
                        subgraph.node(part_model.full_name, shape="diamond", fillcolor=self.COLOR_NODE_ACTIVE)
                    else:
                        subgraph.node(part_model.full_name, shape="diamond", fillcolor=self.COLOR_NODE_DEFAULT)
                else:
                    # Steps as rectangles, color if it is the active part
                    if self.experiment_model.part_path and \
                       part_model.full_name == self.experiment_model.part_path[-1]:
                        subgraph.node(part_model.full_name, fillcolor=self.COLOR_NODE_ACTIVE)
                    else:
                        subgraph.node(part_model.full_name, fillcolor=self.COLOR_NODE_DEFAULT)

    def _collect_path_edges_to_highlight(self, flow_full_name: str, begin_node: str | None) -> set[tuple[str, str]]:
        """
        Collect edges in the recent path to highlight, for the active flow.
        Includes begin and end node edges. Assumes part_path is ordered from first to current part.
        """
        path_edges_to_highlight = set()
        # No edges to highlight if this flow is not active
        active_flow = self.experiment_model.flow_stack[-1] if self.experiment_model.flow_stack else ""
        if flow_full_name != active_flow:
            return path_edges_to_highlight
        path = self.experiment_model.part_path
        path_length = len(path)
        # Highlight the most recent NUM_PATH_EDGES_TO_HIGHLIGHT transitions in the path
        # (from start to current, not reversed)
        start_idx = max(0, path_length - self.NUM_PATH_EDGES_TO_HIGHLIGHT - 1)
        # If at the beginning of the experiment, include the begin edge
        if start_idx == 0 and begin_node and path_length > 0:
            path_edges_to_highlight.add((begin_node, path[0]))
        # Highlight the most recent transitions in the path
        for i in range(start_idx, path_length - 1):
            src = path[i]
            dst = path[i + 1]
            if src is None or dst is None:
                continue
            # If src is the flow and dst is a part inside the flow, use the flow's begin node as src
            if src == active_flow and begin_node:
                src = begin_node
            # If src is not in the active flow, skip highlighting
            elif not self._is_child(src, active_flow):
                continue
            # If dst is an ending (done/quit), use the correct node name
            if dst in ("done", "quit"):
                dst = f"{dst}_{active_flow}" if active_flow else dst
            # If dst is not in the active flow, skip highlighting
            elif not self._is_child(dst, active_flow):
                continue
            path_edges_to_highlight.add((src, dst))
        return path_edges_to_highlight

    def _add_edges_and_endings(self, flow_full_name: str, subgraph: graphviz.Digraph, path_edges_to_highlight: set[tuple[str, str]], begin_node: str | None, first_part_full: str | None) -> None:
        """
        Add edges between parts, including begin edge, next_part edges, and ending nodes/edges.
        """
        # Add begin edge, highlight if in path
        if begin_node and first_part_full:
            self._add_normal_edge(subgraph, begin_node, first_part_full, path_edges_to_highlight)

        # Add edges based on next_part and statements configurations
        for part_full_name, part_model in self.experiment_model.experiment_parts.items():
            if self._is_child(part_full_name, flow_full_name):
                next_parts_full_names = []
                next_part_raw = part_model.raw_config.get("next_part")
                if next_part_raw is None:
                    if part_model.part_category == "decision":
                        statements = part_model.raw_config.get("config_values", {}).get("statements")
                        if isinstance(statements, list):
                            for statement in statements:
                                if isinstance(statement, str):
                                    if " if " in statement:
                                        route_name = statement.split(" if ")[0].strip()
                                    elif "else" in statement:
                                        route_name = statement.split("else")[1].strip()
                                    else:
                                        route_name = statement.strip()
                                    if route_name in ("done", "quit"):
                                        self._add_ending_node(subgraph, part_full_name, route_name, flow_full_name, path_edges_to_highlight)
                                    else:
                                        next_parts_full_names.append(self._to_full_name(route_name, flow_full_name))
                elif isinstance(next_part_raw, str):
                    if next_part_raw in ("done", "quit"):
                        self._add_ending_node(subgraph, part_full_name, next_part_raw, flow_full_name, path_edges_to_highlight)
                    else:
                        next_parts_full_names.append(self._to_full_name(next_part_raw, flow_full_name))
                elif isinstance(next_part_raw, dict) and next_part_raw:
                    for route, next_part_name in next_part_raw.items():
                        if next_part_name in ("done", "quit"):
                            self._add_ending_node(subgraph, part_full_name, next_part_name, flow_full_name, path_edges_to_highlight)
                        else:
                            next_parts_full_names.append(self._to_full_name(next_part_name, flow_full_name))
                else:
                    raise ValueError(f"Invalid next_part format: {next_part_raw}")

                for next_part_full_name in next_parts_full_names:
                    if next_part_full_name in self.experiment_model.experiment_parts:
                        self._add_normal_edge(subgraph, part_full_name, next_part_full_name, path_edges_to_highlight)

    def _add_normal_edge(self, subgraph, src: str, dst: str, path_edges_to_highlight: set[tuple[str, str]]) -> None:
        """
        Add a normal edge from src to dst, with highlighting if needed.
        """
        color = self.COLOR_EDGE_ACTIVE if (src, dst) in path_edges_to_highlight else self.COLOR_EDGE_DEFAULT
        subgraph.edge(src, dst, color=color)
    
    def _add_ending_node(self, subgraph, part_full_name: str, ending_name: str, flow_full_name: str, path_edges_to_highlight: set[tuple[str, str]]) -> None:
        """
        Add an ending node (done/quit) and edge from part_full_name to it, with highlighting if needed.
        Highlight the end node if the path ends at this ending.
        """
        end_node = f"{ending_name}_{flow_full_name}" if flow_full_name else ending_name
        path = self.experiment_model.part_path
        highlight_end = False
        # Highlight end node if path ends at this ending
        if path and path[-1] in ("done", "quit") and \
            ending_name == path[-1] and \
            flow_full_name == self.experiment_model.flow_stack[-1]:
            highlight_end = True
        node_fill = self.COLOR_NODE_END_ACTIVE if highlight_end else self.COLOR_NODE_END_DEFAULT
        subgraph.node(end_node, label=ending_name, shape="doublecircle", style="filled", fillcolor=node_fill)
        color = self.COLOR_EDGE_ACTIVE if (part_full_name, end_node) in path_edges_to_highlight else self.COLOR_EDGE_DEFAULT
        subgraph.edge(part_full_name, end_node, color=color)

    def _is_child(self, part_full_name: str | None, flow_full_name: str) -> bool:
        # Check if the part is a direct child of the given flow
        # Note: grandchildren are not included
        if part_full_name is None:
            return False
        if flow_full_name == "":
            return "." not in part_full_name
        return part_full_name.startswith(flow_full_name + ".") and \
            part_full_name.count(".") == flow_full_name.count(".") + 1
    
    def _to_full_name(self, name: str, parent_full_name: str) -> str:
        if not name:
            return ""
        if parent_full_name == "":
            return name
        return parent_full_name + "." + name
