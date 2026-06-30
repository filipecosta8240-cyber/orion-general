from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .memory import MemoryEntry, ObsidianMemoryBridge

logger = logging.getLogger("orion.knowledge_graph")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
GRAPH_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "KNOWLEDGE_GRAPH"


@dataclass
class GraphNode:
    id: str
    label: str
    node_type: str
    properties: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""
    salience: float = 0.5

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


@dataclass
class GraphEdge:
    id: str
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    created_at: str = ""

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


class KnowledgeGraph:
    def __init__(self, memory: ObsidianMemoryBridge, graph_root: Optional[Path] = None):
        self.memory = memory
        self.graph_root = graph_root or GRAPH_ROOT
        self.graph_root.mkdir(parents=True, exist_ok=True)
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        self._adjacency: Dict[str, Set[str]] = defaultdict(set)
        self._load_graph()

    def _load_graph(self) -> None:
        nodes_file = self.graph_root / "nodes.json"
        edges_file = self.graph_root / "edges.json"
        if nodes_file.exists():
            try:
                data = json.loads(nodes_file.read_text(encoding="utf-8"))
                for nid, ndata in data.items():
                    self._nodes[nid] = GraphNode(**ndata)
            except (json.JSONDecodeError, TypeError):
                pass
        if edges_file.exists():
            try:
                data = json.loads(edges_file.read_text(encoding="utf-8"))
                for eid, edata in data.items():
                    edge = GraphEdge(**edata)
                    self._edges[eid] = edge
                    self._adjacency[edge.source_id].add(eid)
                    self._adjacency[edge.target_id].add(eid)
            except (json.JSONDecodeError, TypeError):
                pass

    def _save_graph(self) -> None:
        nodes_file = self.graph_root / "nodes.json"
        edges_file = self.graph_root / "edges.json"
        nodes_data = {nid: n.to_dict() for nid, n in self._nodes.items()}
        edges_data = {eid: e.to_dict() for eid, e in self._edges.items()}
        nodes_file.write_text(json.dumps(nodes_data, indent=2, ensure_ascii=False), encoding="utf-8")
        edges_file.write_text(json.dumps(edges_data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _new_id(self, prefix: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        return f"{prefix}_{ts[:20]}"

    def add_node(self, label: str, node_type: str, properties: Optional[Dict[str, str]] = None, salience: float = 0.5) -> GraphNode:
        for node in self._nodes.values():
            if node.label.lower() == label.lower() and node.node_type == node_type:
                node.salience = min(1.0, node.salience + 0.1)
                self._save_graph()
                return node
        node_id = self._new_id("n")
        node = GraphNode(
            id=node_id,
            label=label,
            node_type=node_type,
            properties=properties or {},
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            salience=salience,
        )
        self._nodes[node_id] = node
        self._save_graph()
        logger.info("Nó adicionado: %s (%s)", label, node_type)
        return node

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0) -> Optional[GraphEdge]:
        if source_id not in self._nodes or target_id not in self._nodes:
            return None
        for edge in self._edges.values():
            if edge.source_id == source_id and edge.target_id == target_id and edge.relation == relation:
                edge.weight = min(5.0, edge.weight + 0.2)
                self._save_graph()
                return edge
        edge_id = self._new_id("e")
        edge = GraphEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self._edges[edge_id] = edge
        self._adjacency[source_id].add(edge_id)
        self._adjacency[target_id].add(edge_id)
        self._save_graph()
        logger.info("Aresta adicionada: %s --[%s]--> %s", source_id, relation, target_id)
        return edge

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        return self._nodes.get(node_id)

    def find_node(self, label: str) -> List[GraphNode]:
        return [n for n in self._nodes.values() if label.lower() in n.label.lower()]

    def get_neighbors(self, node_id: str) -> List[Tuple[GraphNode, GraphEdge]]:
        results = []
        for edge_id in self._adjacency.get(node_id, set()):
            edge = self._edges.get(edge_id)
            if not edge:
                continue
            neighbor_id = edge.target_id if edge.source_id == node_id else edge.source_id
            neighbor = self._nodes.get(neighbor_id)
            if neighbor:
                results.append((neighbor, edge))
        return sorted(results, key=lambda x: x[1].weight, reverse=True)

    def extract_entities_from_text(self, text: str) -> List[Tuple[str, str]]:
        entities = []
        patterns = {
            "concept": r"\b(?:seguran[cç]a|otimiza[cç][aã]o|valida[cç][aã]o|mem[oó]ria|agente|framework|sistema|padr[aã]o|an[aá]lise|pesquisa|estrat[eé]gia|dom[ií]nio|ferramenta|conhecimento|habilidade|tarefa|objetivo|regra|pol[ií]tica|arquitetura|dados|informa[cç][aã]o|recurso|processo|m[eé]todo|resultado|efici[eê]ncia|qualidade|desempenho)\b",
            "tool": r"\b(?:ResearchTool|PromptTool|ValidationTool|ORION|MemGPT|Letta|LangGraph|CrewAI|FAISS|ChromaDB|SQLite|Neo4j)\b",
            "agent": r"\b(?:Drag[aã]o|Elias|Pesquisador|Estratega|Documentalista)\b",
            "domain": r"\b(?:avicultura|sa[uú]de|seguran[cç]a|economia|educa[cç][aã]o|tecnologia|ci[eê]ncia|medicina|engenharia|direito)\b",
        }
        for etype, pattern in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                entities.append((match.group(), etype))
        return list(set(entities))

    def build_from_memory(self) -> int:
        entries = self.memory.list_entries()
        new_nodes = 0
        for entry in entries:
            entities = self.extract_entities_from_text(f"{entry.title} {entry.content}")
            node_ids = []
            for entity_text, entity_type in entities:
                node = self.add_node(entity_text, entity_type)
                node_ids.append(node.id)
                new_nodes += 1
            for i in range(len(node_ids)):
                for j in range(i + 1, len(node_ids)):
                    self.add_edge(node_ids[i], node_ids[j], "related_to")
        logger.info("Grafo construído: %d nós adicionados", new_nodes)
        return new_nodes

    def query(self, start_label: str, max_depth: int = 2) -> Dict[str, object]:
        start_nodes = self.find_node(start_label)
        if not start_nodes:
            return {"start": start_label, "paths": []}
        start = start_nodes[0]
        visited = set()
        paths = []
        queue = [(start.id, [], 0)]
        while queue:
            current_id, path, depth = queue.pop(0)
            if depth > max_depth or current_id in visited:
                continue
            visited.add(current_id)
            current_node = self._nodes.get(current_id)
            if not current_node:
                continue
            for neighbor, edge in self.get_neighbors(current_id):
                if neighbor.id not in visited:
                    new_path = path + [{
                        "from": current_node.label,
                        "relation": edge.relation,
                        "to": neighbor.label,
                        "weight": edge.weight,
                    }]
                    paths.append(new_path)
                    queue.append((neighbor.id, new_path, depth + 1))
        return {"start": start.label, "total_nodes": len(self._nodes), "total_edges": len(self._edges), "paths": paths[:20]}

    def get_stats(self) -> Dict[str, object]:
        type_counts = defaultdict(int)
        for node in self._nodes.values():
            type_counts[node.node_type] += 1
        rel_counts = defaultdict(int)
        for edge in self._edges.values():
            rel_counts[edge.relation] += 1
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "node_types": dict(type_counts),
            "relation_types": dict(rel_counts),
        }


class KnowledgeGraphQueryEngine:
    """Natural language query interface for the knowledge graph."""

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def ask(self, question: str) -> str:
        q = question.lower().strip()

        if any(w in q for w in ["como", "quantos", "quantas"]):
            return self._count_answer(q)
        if any(w in q for w in ["relacion", "conect", "lig", "vizinh"]):
            return self._neighbors_answer(q)
        if any(w in q for w in ["o que", "quais", "liste", "listar", "mostre"]):
            return self._list_answer(q)
        if any(w in q for w in ["dominio", "domínio", "assunto", "tema"]):
            return self._domain_answer(q)
        if any(w in q for w in ["ferramenta", "tool", "agente"]):
            return self._type_answer(q, ["tool", "agent"])
        if any(w in q for w in ["estatisticas", "stats", "resumo"]):
            return self._stats_answer()
        return self._general_answer(q)

    def _count_answer(self, question: str) -> str:
        stats = self.graph.get_stats()
        if "nó" in question or "node" in question or "entidade" in question:
            return f"O grafo tem {stats['total_nodes']} nós (entidades)."
        if "aresta" in question or "edge" in question or "relação" in question:
            return f"O grafo tem {stats['total_edges']} arestas (relações)."
        return f"Grafo: {stats['total_nodes']} nós, {stats['total_edges']} arestas."

    def _neighbors_answer(self, question: str) -> str:
        words = question.split()
        for word in words:
            found = self.graph.find_node(word)
            if found:
                node = found[0]
                neighbors = self.graph.get_neighbors(node.id)
                if not neighbors:
                    return f"'{node.label}' não tem vizinhos no grafo."
                lines = [f"Vizinhos de '{node.label}':"]
                for neighbor, edge in neighbors[:10]:
                    lines.append(f"  - {neighbor.label} ({edge.relation}, peso={edge.weight:.1f})")
                return "\n".join(lines)
        return "Não encontrei a entidade mencionada no grafo."

    def _list_answer(self, question: str) -> str:
        if "dominio" in question or "domínio" in question or "assunto" in question:
            nodes = [n for n in self.graph._nodes.values() if n.node_type == "domain"]
        elif "ferramenta" in question or "tool" in question:
            nodes = [n for n in self.graph._nodes.values() if n.node_type == "tool"]
        elif "agente" in question or "agent" in question:
            nodes = [n for n in self.graph._nodes.values() if n.node_type == "agent"]
        else:
            nodes = list(self.graph._nodes.values())
        if not nodes:
            return "Nenhum item encontrado para essa categoria."
        nodes.sort(key=lambda n: n.salience, reverse=True)
        lines = [f"Encontrados {len(nodes)} itens:"]
        for n in nodes[:15]:
            lines.append(f"  - {n.label} (tipo={n.node_type}, salience={n.salience:.2f})")
        return "\n".join(lines)

    def _domain_answer(self, question: str) -> str:
        domains = [n for n in self.graph._nodes.values() if n.node_type == "domain"]
        if not domains:
            return "Nenhum domínio encontrado no grafo."
        lines = ["Domínios no grafo:"]
        for d in domains:
            neighbors = self.graph.get_neighbors(d.id)
            connected = [n.label for n, _ in neighbors[:5]]
            lines.append(f"  - {d.label} (conectado a: {', '.join(connected) if connected else 'nenhum'})")
        return "\n".join(lines)

    def _type_answer(self, question: str, types: List[str]) -> str:
        nodes = [n for n in self.graph._nodes.values() if n.node_type in types]
        if not nodes:
            return "Nenhum item encontrado para essa categoria."
        lines = [f"Itens do tipo {', '.join(types)}:"]
        for n in nodes:
            lines.append(f"  - {n.label} (salience={n.salience:.2f})")
        return "\n".join(lines)

    def _stats_answer(self) -> str:
        stats = self.graph.get_stats()
        lines = [
            "Estatísticas do grafo de conhecimento:",
            f"  Total de nós: {stats['total_nodes']}",
            f"  Total de arestas: {stats['total_edges']}",
            "  Tipos de nós:",
        ]
        for t, c in stats['node_types'].items():
            lines.append(f"    - {t}: {c}")
        lines.append("  Tipos de relações:")
        for t, c in stats['relation_types'].items():
            lines.append(f"    - {t}: {c}")
        return "\n".join(lines)

    def _general_answer(self, question: str) -> str:
        words = [w for w in question.split() if len(w) > 3]
        for word in words:
            found = self.graph.find_node(word)
            if found:
                node = found[0]
                result = self.graph.query(node.label, max_depth=1)
                if result["paths"]:
                    lines = [f"Resultado para '{node.label}' ({node.node_type}):"]
                    for path in result["paths"][:5]:
                        if path:
                            lines.append(f"  {path[0]['from']} --[{path[0]['relation']}]--> {path[0]['to']}")
                    return "\n".join(lines)
        return "Não encontrei resultados para sua pergunta no grafo de conhecimento."
