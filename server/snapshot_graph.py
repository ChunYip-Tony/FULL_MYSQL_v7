"""Lossless JSON storage for shared snapshot graphs, without alias expansion."""
import json
from dataclasses import fields, is_dataclass


def dumps(snapshot):
    nodes, seen = [], {}

    def encode(value):
        dataclass = is_dataclass(value) and not isinstance(value, type)
        if dataclass or isinstance(value, (dict, list, tuple)):
            identity = id(value)
            if identity in seen:
                return {"ref": seen[identity]}
            index = len(nodes)
            seen[identity] = index
            node = {"kind": "dict" if dataclass or isinstance(value, dict) else "list", "items": []}
            nodes.append(node)
            if dataclass:
                items = ((f.name, getattr(value, f.name)) for f in fields(value))
            elif isinstance(value, dict):
                items = value.items()
            else:
                items = None
            node["items"] = [[k, encode(v)] for k, v in items] if items is not None else [encode(v) for v in value]
            return {"ref": index}
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    root = encode(snapshot)
    return json.dumps({"app_ready_graph_version": 1, "root": root, "nodes": nodes}, separators=(",", ":"))


def loads(payload):
    value = json.loads(payload)
    if not isinstance(value, dict) or "app_ready_graph_version" not in value:
        return value  # Existing complete generations remain readable.
    if value["app_ready_graph_version"] != 1:
        raise ValueError("Unsupported App Ready graph version")
    nodes = value["nodes"]
    objects = []
    for node in nodes:
        if node["kind"] not in {"dict", "list"}:
            raise ValueError("Invalid App Ready graph node")
        objects.append({} if node["kind"] == "dict" else [])

    def decode(item):
        if isinstance(item, dict):
            if set(item) != {"ref"} or type(item["ref"]) is not int or not 0 <= item["ref"] < len(objects):
                raise ValueError("Invalid App Ready graph reference")
            return objects[item["ref"]]
        return item

    for node, target in zip(nodes, objects):
        if node["kind"] == "dict":
            target.update((k, decode(v)) for k, v in node["items"])
        else:
            target.extend(decode(v) for v in node["items"])
    return decode(value["root"])
