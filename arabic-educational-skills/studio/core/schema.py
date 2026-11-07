"""مدقق JSON Schema مدمج (بلا اعتماديات). يدعم المجموعة التي تستعملها مخططات المهارة:
type, enum, const, required, properties, additionalProperties, items, minItems, maxItems, minLength, maxLength,
minimum, maximum, exclusiveMinimum, pattern, anyOf, oneOf, allOf, $ref المحلي (#/...). ما لا يدعمه يُرفَض صراحة
بدل أن يُتجاهل بصمت (unsupported keyword) كي لا يمرّ مستند بلا تحقق."""
import json
import re
from pathlib import Path

SUPPORTED = {"$schema", "$id", "$defs", "definitions", "title", "description", "default", "examples", "$comment", "type", "enum",
             "const", "required", "properties", "additionalProperties", "items", "minItems", "maxItems", "minLength",
             "maxLength", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "pattern", "anyOf", "oneOf",
             "allOf", "$ref", "uniqueItems", "format"}
_T = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _T[t]) and not (t != "boolean" and isinstance(v, bool) and t in ("object", "array", "string"))


def _resolve(root, ref):
    if not ref.startswith("#/"):
        raise ValueError(f"unsupported $ref: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def validate(doc, schema, root=None, path="$"):
    """يعيد قائمة أخطاء نصية (فارغة = صالح)."""
    root = root or schema
    errs = []
    bad = set(schema) - SUPPORTED
    if bad:
        raise ValueError(f"schema keyword(s) not supported by built-in validator: {sorted(bad)} at {path}")
    if "$ref" in schema:
        return validate(doc, _resolve(root, schema["$ref"]), root, path)
    if "type" in schema:
        ts = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_is(doc, t) for t in ts):
            return [f"{path}: expected {'/'.join(ts)}, got {type(doc).__name__}"]
    if "const" in schema and doc != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and doc not in schema["enum"]:
        errs.append(f"{path}: {doc!r} not in {schema['enum']}")
    if isinstance(doc, str):
        if "minLength" in schema and len(doc) < schema["minLength"]:
            errs.append(f"{path}: shorter than {schema['minLength']}")
        if "maxLength" in schema and len(doc) > schema["maxLength"]:
            errs.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], doc):
            errs.append(f"{path}: does not match /{schema['pattern']}/")
    if isinstance(doc, (int, float)) and not isinstance(doc, bool):
        for k, f in (("minimum", lambda a, b: a < b), ("maximum", lambda a, b: a > b),
                     ("exclusiveMinimum", lambda a, b: a <= b), ("exclusiveMaximum", lambda a, b: a >= b)):
            if k in schema and f(doc, schema[k]):
                errs.append(f"{path}: violates {k} {schema[k]}")
    if isinstance(doc, list):
        if "minItems" in schema and len(doc) < schema["minItems"]:
            errs.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(doc) > schema["maxItems"]:
            errs.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True) for x in doc}) != len(doc):
            errs.append(f"{path}: items not unique")
        if "items" in schema:
            for i, x in enumerate(doc):
                errs += validate(x, schema["items"], root, f"{path}[{i}]")
    if isinstance(doc, dict):
        for k in schema.get("required", []):
            if k not in doc:
                errs.append(f"{path}: missing required '{k}'")
        props = schema.get("properties", {})
        for k, v in doc.items():
            if k in props:
                errs += validate(v, props[k], root, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                errs.append(f"{path}: unexpected property '{k}'")
            elif isinstance(schema.get("additionalProperties"), dict):
                errs += validate(v, schema["additionalProperties"], root, f"{path}.{k}")
    if "allOf" in schema:
        for s in schema["allOf"]:
            errs += validate(doc, s, root, path)
    if "anyOf" in schema and not any(not validate(doc, s, root, path) for s in schema["anyOf"]):
        errs.append(f"{path}: matches none of anyOf")
    if "oneOf" in schema and sum(1 for s in schema["oneOf"] if not validate(doc, s, root, path)) != 1:
        errs.append(f"{path}: must match exactly one of oneOf")
    return errs


def load_schema(name_or_path):
    p = Path(name_or_path)
    if not p.exists():
        root = Path(__file__).resolve().parents[2]
        for d in (root / "schemas", root / "references"):
            if (d / name_or_path).exists():
                p = d / name_or_path
                break
    return json.loads(p.read_text("utf-8"))


def validate_file(doc, schema_name):
    return validate(doc, load_schema(schema_name))
