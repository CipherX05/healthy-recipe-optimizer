"""Ingredient substitution network (NetworkX).

Nodes are ingredients that can be swapped and have nutrition data. An edge means
the two have a compatible cooking role. The network answers "what could stand in
for X?"; it does not decide whether a swap is healthier. Scoring does that.

Edge attributes:
  role_score        1.0 same role, 0.6 related role
  flavor_jaccard    FlavorDB2 molecule-set overlap, or None without enough data
  weight            (role_score + flavor_jaccard or 0) / 2, used for layout
"""
from __future__ import annotations

from itertools import combinations

import networkx as nx

from .models import Ingredient

SAME_ROLE = 1.0
RELATED_ROLE = 0.6
# FlavorDB2 lists very few molecules for some foods (1 for ghee, 5 for cream when
# this was written). Jaccard on such a set measures the gap in the data, not the
# food, so thinner profiles count as "not enough data". A project choice.
MIN_PROFILE_MOLECULES = 10
# Pairs inside one family that are still not interchangeable: yogurt or sour cream
# cannot be replaced by a thin milk. (A listed second role, as buttermilk has for
# "milk", still links them.)
UNRELATED_ROLES = frozenset({frozenset({"cultured_dairy", "milk"})})


def role_score(original: Ingredient, candidate: Ingredient) -> float:
    """1.0 for the same role; 0.6 for the same family or a listed second role; else 0."""
    if not (original.substitutable and candidate.substitutable):
        return 0.0
    if original.role == candidate.role:
        return SAME_ROLE
    if candidate.role in original.also or original.role in candidate.also:
        return RELATED_ROLE
    if (original.family == candidate.family
            and frozenset({original.role, candidate.role}) not in UNRELATED_ROLES):
        return RELATED_ROLE
    return 0.0


def jaccard(a: frozenset[int] | set[int], b: frozenset[int] | set[int]) -> float | None:
    """|A intersect B| / |A union B|. None (unknown) if either set is empty."""
    if not a or not b:
        return None
    return len(a & b) / len(a | b)


def flavor_similarity(a: Ingredient, b: Ingredient) -> float | None:
    """Jaccard of the two molecule sets, or None if either profile is too thin."""
    if min(len(a.molecules), len(b.molecules)) < MIN_PROFILE_MOLECULES:
        return None
    return jaccard(a.molecules, b.molecules)


def build_graph(ingredients: dict[str, Ingredient]) -> nx.Graph:
    graph = nx.Graph()
    usable = [i for i in ingredients.values() if i.substitutable and i.nutrients]
    for item in sorted(usable, key=lambda i: i.id):
        graph.add_node(item.id, name=item.name, role=item.role, family=item.family)
    for a, b in combinations(sorted(usable, key=lambda i: i.id), 2):
        score = role_score(a, b)
        if score <= 0:
            continue
        flavor = flavor_similarity(a, b)
        graph.add_edge(
            a.id, b.id,
            role_score=score,
            flavor_jaccard=flavor,
            shared_molecules=len(a.molecules & b.molecules),
            same_flavor_entity=bool(a.flavor_entity_id and a.flavor_entity_id == b.flavor_entity_id),
            weight=(score + (flavor or 0.0)) / 2,
        )
    return graph


def neighbours(graph: nx.Graph, ingredient_id: str) -> list[str]:
    return sorted(graph.neighbors(ingredient_id)) if ingredient_id in graph else []


def ego(graph: nx.Graph, ingredient_id: str, limit: int = 12) -> dict:
    """The strongest ``limit`` links around one ingredient, as JSON-ready data."""
    if ingredient_id not in graph:
        return {"center": ingredient_id, "nodes": [], "edges": [], "total_neighbours": 0}
    ranked = sorted(graph[ingredient_id].items(), key=lambda kv: (-kv[1]["weight"], kv[0]))
    chosen = [other for other, _ in ranked[:limit]]
    sub = graph.subgraph([ingredient_id, *chosen])
    return {
        "center": ingredient_id,
        "total_neighbours": len(ranked),
        "nodes": [{"id": n, **sub.nodes[n]} for n in [ingredient_id, *chosen]],
        "edges": [{"source": ingredient_id, "target": other, **graph[ingredient_id][other]}
                  for other in chosen],
    }


def write_html(graph: nx.Graph, path, ingredient_id: str | None = None) -> None:
    """Interactive Plotly drawing of the whole network or one neighbourhood."""
    import plotly.graph_objects as go

    if ingredient_id:
        if ingredient_id not in graph:
            raise ValueError(f"{ingredient_id!r} is not in the substitution network")
        graph = nx.ego_graph(graph, ingredient_id)
    layout = nx.spring_layout(graph, seed=42, weight="weight", k=None if ingredient_id else 0.35)
    edge_x, edge_y = [], []
    for a, b in graph.edges():
        edge_x += [layout[a][0], layout[b][0], None]
        edge_y += [layout[a][1], layout[b][1], None]
    figure = go.Figure(go.Scatter(x=edge_x, y=edge_y, mode="lines", hoverinfo="skip",
                                  line={"width": 0.6, "color": "#a39b8b"}, showlegend=False))
    for family in sorted({data["family"] for _, data in graph.nodes(data=True)}):
        members = [n for n, d in graph.nodes(data=True) if d["family"] == family]
        figure.add_trace(go.Scatter(
            x=[layout[n][0] for n in members], y=[layout[n][1] for n in members],
            mode="markers+text" if ingredient_id else "markers", name=family,
            text=[graph.nodes[n]["name"] for n in members], textposition="top center",
            hovertext=[f"{graph.nodes[n]['name']} ({graph.degree(n)} links)" for n in members],
            hoverinfo="text", marker={"size": 11},
        ))
    figure.update_layout(title="Ingredient substitution network (role-compatible links)",
                         xaxis={"visible": False}, yaxis={"visible": False},
                         plot_bgcolor="#fdfdfd", paper_bgcolor="#fdfdfd")
    figure.write_html(str(path), include_plotlyjs=True)
