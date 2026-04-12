from .models import StructureNode


def render_indented(root: StructureNode) -> str:
    if root is None or not root.children:
        return "(none)"

    lines: list[str] = []

    def walk(node: StructureNode, depth: int) -> None:
        if node.label:
            lines.append(f"{'  ' * depth}{node.label}")
        next_depth = depth + (1 if node.label else 0)
        for child in node.children:
            walk(child, next_depth)

    walk(root, 0)
    return "\n".join(lines) if lines else "(none)"
