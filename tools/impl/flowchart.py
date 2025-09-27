import graphviz
from tools.impl.experiment_model import ExperimentModel

class FlowChart:
    """
    Converts an experiment model into a flowchart visualization
    using Graphviz.
    """
    def __init__(self, experiment_model: ExperimentModel):
        self.experiment_model = experiment_model
        self.graph = graphviz.Digraph(
            format="png",
            node_attr={"shape": "box", "style": "rounded,filled", "fillcolor": "lightgrey"},
            edge_attr={"color": "black"},
        )
        with self.graph.subgraph(name="Experiment Flowchart") as subgraph:
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
        # Determine the active flow
        active_flow = ""
        if self.experiment_model.flow_stack:
            active_flow = self.experiment_model.flow_stack[-1]

        # For each part in the flow, add it to the subgraph
        for part_full_name, part_model in self.experiment_model.experiment_parts.items():
            if self._is_child(part_full_name, flow_full_name):
                if part_model.part_category == "flow":
                    # Create a subgraph for the nested flow, color if the active flow or active part
                    if self.experiment_model.part_path and \
                       part_model.full_name == self.experiment_model.part_path[-1]:
                        subgraph.node(part_model.full_name, shape="component", fillcolor="orange")
                    elif active_flow and part_model.full_name == active_flow:
                        subgraph.node(part_model.full_name, shape="component", fillcolor="darkorange")
                    else:
                        subgraph.node(part_model.full_name, shape="component", fillcolor="lightgrey")
                    with subgraph.subgraph(name=part_model.full_name) as child_subgraph:
                        self._populate_subgraph(part_model.full_name, child_subgraph)
                elif part_model.part_category == "decision":
                    # Decision parts as diamonds, color orange if it is the active part
                    if self.experiment_model.part_path and \
                       part_model.full_name == self.experiment_model.part_path[-1]:
                        subgraph.node(part_model.full_name, shape="diamond", fillcolor="orange")
                    else:
                        subgraph.node(part_model.full_name, shape="diamond", fillcolor="lightgrey")
                else:
                    # Steps as rectangles, color bright if it is the active part
                    if self.experiment_model.part_path and \
                       part_model.full_name == self.experiment_model.part_path[-1]:
                        subgraph.node(part_model.full_name, fillcolor="orange")
                    else:
                        subgraph.node(part_model.full_name, fillcolor="lightgrey")

        # Identify edges between parts that are in the recent path taken
        # and highlight them in orange
        NUM_PATH_NODES_TO_HIGHLIGHT = 3
        path_length = len(self.experiment_model.part_path)
        path_edges_to_highlight = set()
        for i in range(max(0, path_length - NUM_PATH_NODES_TO_HIGHLIGHT), path_length - 1):
            src = self.experiment_model.part_path[i]
            dst = self.experiment_model.part_path[i + 1]
            if src in self.experiment_model.experiment_parts and \
                dst in self.experiment_model.experiment_parts and \
                self._is_child(src, flow_full_name) and \
                self._is_child(dst, flow_full_name) and \
                self._is_child(src, active_flow) and \
                self._is_child(dst, active_flow):
                path_edges_to_highlight.add((src, dst))
                subgraph.edge(src, dst, color="orange")

        # Next, add next_part edges only if not in path_edges_to_highlight
        # We want the next_part edges to be less prominent than the path edges
        # Note: we also check the 'statements' config for decision parts without
        # a next_part config, as those statements also define possible next parts
        # in a shorthand way.
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
                                    next_parts_full_names.append(
                                        self._to_full_name(route_name, flow_full_name)
                                    )
                elif isinstance(next_part_raw, str):
                    next_parts_full_names.append(
                        self._to_full_name(next_part_raw, flow_full_name)
                    )
                elif isinstance(next_part_raw, dict) and next_part_raw:
                    for route, next_part_name in next_part_raw.items():
                        next_parts_full_names.append(
                            self._to_full_name(next_part_name, flow_full_name)
                        )
                else:
                    raise ValueError(f"Invalid next_part format: {next_part_raw}")

                for next_part_full_name in next_parts_full_names:
                    if next_part_full_name in self.experiment_model.experiment_parts:
                        if (part_full_name, next_part_full_name) not in path_edges_to_highlight:
                            subgraph.edge(part_full_name, next_part_full_name, color="grey")

    def _is_child(self, part_full_name: str, flow_full_name: str) -> bool:
        # Check if the part is a direct child of the given flow
        # Note: grandchildren are not included
        if flow_full_name == "":
            return "." not in part_full_name
        return part_full_name.startswith(flow_full_name + ".") and \
            part_full_name.count(".") == flow_full_name.count(".") + 1
    
    def _to_full_name(self, name: str, parent_full_name: str) -> str:
        if parent_full_name == "":
            return name
        return parent_full_name + "." + name
    
    def _to_short_name(self, full_name: str) -> str:
        return full_name.split(".")[-1]
