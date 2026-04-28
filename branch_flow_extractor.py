# branch_flow_extractor.py

from typing import Any, Dict, List, Optional


class BranchFlowExtractor:
    """
    Convert a validated branch diagram object into Mermaid flowchart code.

    This class does NOT call Ollama.
    It only receives the validated Router result and converts it into Mermaid.
    """

    def __init__(self, branch_diagram: Any):
        self.diagram = self._to_dict(branch_diagram)
        self.nodes = self.diagram.get("nodes", [])
        self.edges = self.diagram.get("edges", [])
        self.direction = self.diagram.get("direction", "TD")

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """
        Support:
        1. Pydantic v2 object: model_dump()
        2. Pydantic v1 object: dict()
        3. normal dict
        """

        if isinstance(obj, dict):
            return obj

        if hasattr(obj, "model_dump"):
            return obj.model_dump()

        if hasattr(obj, "dict"):
            return obj.dict()

        raise TypeError("Unsupported branch diagram type. Expected dict or Pydantic model.")

    def _escape_text(self, text: Optional[str]) -> str:
        """
        Escape text for Mermaid node labels.
        """

        if text is None:
            return ""

        return str(text).replace('"', '\\"')

    def _validate(self) -> None:
        """
        Basic validation after Pydantic validation.
        This checks graph-level consistency.
        """

        node_ids = [node.get("id") for node in self.nodes]

        if len(node_ids) != len(set(node_ids)):
            raise ValueError("Duplicate node id found in branch diagram.")

        node_id_set = set(node_ids)

        for edge in self.edges:
            source = edge.get("source")
            target = edge.get("target")

            if source not in node_id_set:
                raise ValueError(f"Edge source '{source}' does not exist in nodes.")

            if target not in node_id_set:
                raise ValueError(f"Edge target '{target}' does not exist in nodes.")

    def _node_to_mermaid(self, node: Dict[str, Any]) -> str:
        """
        Convert one node to Mermaid syntax.

        process  -> A["text"]
        decision -> B{"text"}
        """

        node_id = node.get("id")
        text = self._escape_text(node.get("text"))
        kind = node.get("kind", "process")

        if kind == "decision":
            return f'    {node_id}{{"{text}"}}'

        return f'    {node_id}["{text}"]'

    def _edge_to_mermaid(self, edge: Dict[str, Any]) -> str:
        """
        Convert one edge to Mermaid syntax.

        Without label:
            A --> B

        With label:
            B -->|正确| C
        """

        source = edge.get("source")
        target = edge.get("target")
        label = edge.get("label")

        if label is None or label == "":
            return f"    {source} --> {target}"

        label = self._escape_text(label)
        return f"    {source} -->|{label}| {target}"

    def to_mermaid(self) -> str:
        """
        Generate Mermaid flowchart code.
        """

        self._validate()

        lines: List[str] = []

        lines.append(f"flowchart {self.direction}")

        for node in self.nodes:
            lines.append(self._node_to_mermaid(node))

        for edge in self.edges:
            lines.append(self._edge_to_mermaid(edge))

        return "\n".join(lines)