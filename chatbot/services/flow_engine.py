from __future__ import annotations

from typing import Optional

from chatbot.models import ChatbotFlow, ChatbotNode, ChatbotEdge


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _find_start_node(flow: ChatbotFlow) -> Optional[ChatbotNode]:
    return flow.nodes.filter(node_type="start").first()


def _get_node(flow: ChatbotFlow, node_id: str) -> Optional[ChatbotNode]:
    return flow.nodes.filter(node_id=node_id).first()


def _pick_edge(flow: ChatbotFlow, node_id: str, message: str) -> Optional[ChatbotEdge]:
    message = _normalize(message)
    edges = list(flow.edges.filter(source_id=node_id))
    for edge in edges:
        if edge.condition_text and edge.condition_text.lower() in message:
            return edge
    for edge in edges:
        if edge.is_default:
            return edge
    return edges[0] if edges else None


def run_flow(message: str) -> Optional[str]:
    flow = ChatbotFlow.objects.filter(is_active=True).order_by("-created_at").first()
    if not flow:
        return None

    node = _find_start_node(flow)
    if not node:
        return None

    steps = 0
    while node and steps < 10:
        steps += 1
        if node.node_type in ["message", "action", "end"]:
            text = node.data.get("text") if node.data else None
            return text or None

        if node.node_type == "condition":
            edge = _pick_edge(flow, node.node_id, message)
            if not edge:
                return None
            node = _get_node(flow, edge.target_id)
            continue

        if node.node_type == "start":
            edge = _pick_edge(flow, node.node_id, message)
            if not edge:
                return None
            node = _get_node(flow, edge.target_id)
            continue

        # Unknown node type
        return None

    return None
