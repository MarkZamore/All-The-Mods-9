"""Pure, opt-in ATM9 schema2 locale/display validation. Never writes or downloads.

The legacy profile is deliberately not handled here. Callers keep its frozen
reader and pass only explicitly selected schema2 quest-localization rows here.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path

KIND = "atm9-native-locale-display"
PROFILE_KIND = "ftbquests-russian-display-localization"
EN = "kubejs/assets/kubejs/lang/en_us.json"
RU = "kubejs/assets/kubejs/lang/ru_ru.json"
MANIFEST = "tools/atm9_ru_future/generated-profile.json"
PATCH_TOOL = "tools/atm9_ru_display.py"
PATCH_SHA = "03db33eb4adc95036d0f8b18885b421bfb9177a678346aed87e51522c45f731b"
LEGACY_SHA = "9ebb5aca30cc15ecdd231e534fc1a77d8af6377943ef9b76b6143e848725fde6"
ALIASES_SHA = "14934a23affb96356d067f3f736e3fd3a7428393720d4706521fdfaf21ba5a61"
FIELDS = {"schemaVersion", "kind", "sourceVersion", "upstreamLockSha256",
          "manifestPath", "manifestSha256", "patchTool", "patchToolSha256", "russianRole"}
DISPLAY = {"title", "subtitle", "description", "hover"}
ALIAS = re.compile(r"\{(atm9\.translation\.inline\.[0-9a-f]{24})\}")
ALIAS_KEY = re.compile(r"atm9\.translation\.inline\.[0-9a-f]{24}")
NATIVE_KEY = re.compile(r"[A-Za-z0-9_.-]+")
NATIVE_REFERENCE = re.compile(r"\{([A-Za-z0-9_.-]+)\}")
SHA = re.compile("[0-9a-f]{64}")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("Duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(data):
    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=pairs)


def resource(pack, relative):
    if (not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative or
            any(p in {"", ".", ".."} or any(ord(c) < 32 for c in p) for p in relative.split("/"))):
        raise ValueError("Unsafe profile path")
    root = Path(pack)
    path = root
    for part in [None, *relative.split("/")]:
        if part is not None:
            path /= part
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Linked profile path: " + relative)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Profile path leaves pack")
    return path


def read_pin(pack, relative, expected, *, limit=32 * 1024 * 1024):
    if not isinstance(expected, str) or not SHA.fullmatch(expected):
        raise ValueError("Invalid pinned SHA256")
    path = resource(pack, relative)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Missing/oversized pinned profile file: " + relative)
    raw = path.read_bytes()
    if digest(raw) != expected:
        raise ValueError("Profile file SHA256 mismatch: " + relative)
    return raw


def index_rows(rows, label):
    if not isinstance(rows, list):
        raise ValueError("Invalid " + label)
    result = {}
    folded = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid " + label + " row")
        relative = row.get("path")
        # Validate spelling without accessing a real pack.
        if (not isinstance(relative, str) or not relative or relative.startswith("/") or
                "\\" in relative or ":" in relative or any(p in {"", ".", ".."} or
                any(ord(c) < 32 for c in p) for p in relative.split("/"))):
            raise ValueError("Unsafe " + label + " path")
        if relative.casefold() in folded:
            raise ValueError("Duplicate " + label + " path")
        folded.add(relative.casefold())
        if (type(row.get("sizeBytes")) is not int or row["sizeBytes"] < 0 or
                not isinstance(row.get("sha256"), str) or not SHA.fullmatch(row["sha256"])):
            raise ValueError("Invalid " + label + " size/SHA256")
        result[relative] = row
    return result


class Node:
    def __init__(self, value, start, end, children=None):
        self.value, self.start, self.end, self.children = value, start, end, children


class Snbt:
    """Read-only token tree; keep exact source spans, never serialize quest data."""
    def __init__(self, text):
        self.text, self.i = text, 0

    def skip(self):
        while self.i < len(self.text):
            c = self.text[self.i]
            if c.isspace() or c == "," or (self.i == 0 and c == "\ufeff"):
                self.i += 1
            elif self.text.startswith("//", self.i) or c == "#":
                end = self.text.find("\n", self.i)
                self.i = len(self.text) if end < 0 else end + 1
            else:
                return

    def quoted(self):
        start, quote = self.i, self.text[self.i]
        self.i += 1
        while self.i < len(self.text):
            c = self.text[self.i]
            self.i += 1
            if c == "\\":
                self.i += 1
            elif c == quote:
                raw = self.text[start:self.i]
                if quote == '"':
                    return json.loads(raw)
                # Native single-quoted strings only need quote/backslash escapes.
                return re.sub(r"\\(['\\])", r"\1", raw[1:-1])
        raise ValueError("Unclosed SNBT string")

    def value(self):
        self.skip()
        start = self.i
        if self.i >= len(self.text):
            raise ValueError("Missing SNBT value")
        c = self.text[self.i]
        if c in "\"'":
            return Node(self.quoted(), start, self.i)
        if c == "{":
            self.i += 1
            children = {}
            while True:
                self.skip()
                if self.i >= len(self.text):
                    raise ValueError("Unclosed SNBT object")
                if self.text[self.i] == "}":
                    self.i += 1
                    return Node(None, start, self.i, children)
                if self.text[self.i] in "\"'":
                    key = self.quoted()
                else:
                    at = self.i
                    while self.i < len(self.text) and self.text[self.i] not in ": \t\r\n":
                        self.i += 1
                    key = self.text[at:self.i]
                self.skip()
                if not key or key in children or self.i >= len(self.text) or self.text[self.i] != ":":
                    raise ValueError("Malformed/duplicate SNBT key")
                self.i += 1
                children[key] = self.value()
        if c == "[":
            self.i += 1
            children = []
            self.skip()
            if self.i + 1 < len(self.text) and self.text[self.i] in "BIL" and self.text[self.i + 1] == ";":
                self.i += 2
            while True:
                self.skip()
                if self.i >= len(self.text):
                    raise ValueError("Unclosed SNBT list")
                if self.text[self.i] == "]":
                    self.i += 1
                    return Node(None, start, self.i, children)
                children.append(self.value())
        while self.i < len(self.text) and self.text[self.i] not in " \t\r\n,]}":
            self.i += 1
        if self.i == start:
            raise ValueError("Malformed SNBT token")
        return Node(None, start, self.i)

    def parse(self):
        node = self.value()
        self.skip()
        if self.i != len(self.text):
            raise ValueError("Trailing SNBT data")
        return node


def locate(node, trail):
    if not isinstance(trail, list) or not trail:
        raise ValueError("Missing actual display path")
    for part in trail:
        if isinstance(node.children, dict) and type(part) is str and part in node.children:
            node = node.children[part]
        elif isinstance(node.children, list) and type(part) is int and 0 <= part < len(node.children):
            node = node.children[part]
        else:
            raise ValueError("Declared display path does not exist")
    if not isinstance(node.value, str):
        raise ValueError("Display span must be one native string leaf")
    return node


def display_field(trail):
    """Only direct FTB quest-object display fields, never arbitrary NBT keys."""
    if not isinstance(trail, list) or not trail:
        raise ValueError("Missing native display path")
    parts = list(trail)
    listed = type(parts[-1]) is int
    if listed:
        if parts[-1] < 0:
            raise ValueError("Invalid display list index")
        parts.pop()
    if not parts or not isinstance(parts[-1], str):
        raise ValueError("Not a native display field")
    field, prefix = parts[-1], parts[:-1]
    if any(type(p) not in {int, str} for p in prefix):
        raise ValueError("Invalid native display path part")
    shape = tuple(int if type(p) is int and p >= 0 else p for p in prefix)
    text_objects = {(), ("quests", int), ("quests", int, "tasks", int),
                    ("quests", int, "rewards", int), ("chapter_groups", int),
                    ("reward_tables", int), ("reward_tables", int, "rewards", int)}
    images = {("images", int), ("quests", int, "images", int)}
    valid = (shape in text_objects and field in {"title", "subtitle", "description"} or
             shape in images and field == "hover")
    if not valid or listed and field not in {"description", "hover"}:
        raise ValueError("Not a direct native FTB display path")
    return field


def string_table(raw):
    result = parse(raw)
    if not isinstance(result, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in result.items()):
        raise ValueError("Locale overlay is not a native JSON string table")
    return result


def display_aliases(before, after, field):
    """Accept native references or text-to-translate component substitutions.

    Component styles, URLs, click actions and every other non-text member must
    compare exactly. Never reinterpret the whole component as translated text.
    """
    direct = NATIVE_REFERENCE.fullmatch(after)
    if direct:
        return {direct.group(1): before}
    if field == "hover" and NATIVE_KEY.fullmatch(after):
        return {after: before}
    old, new = parse(before.encode()), parse(after.encode())
    found = {}

    def compare(a, b):
        if isinstance(a, dict) and isinstance(b, dict):
            ak, bk = set(a), set(b)
            if "text" in a and "text" not in b and "translate" not in a and "translate" in b:
                if (ak - {"text"} != bk - {"translate"} or not isinstance(a["text"], str) or
                        not isinstance(b["translate"], str) or not NATIVE_KEY.fullmatch(b["translate"])):
                    raise ValueError("Invalid native component text substitution")
                key = b["translate"]
                if key in found and found[key] != a["text"]:
                    raise ValueError("Component alias combines distinct source text")
                found[key] = a["text"]
                ak, bk = ak - {"text"}, bk - {"translate"}
            if ak != bk:
                raise ValueError("Native component non-text members changed")
            for key in ak:
                compare(a[key], b[key])
        elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            for x, y in zip(a, b):
                compare(x, y)
        elif type(a) is not type(b) or a != b:
            raise ValueError("Native component non-text value changed")

    compare(old, new)
    if not found:
        raise ValueError("Display output must use a native locale alias")
    return found


def validate(pack, descriptor, upstreamBytes, originalRows, baseReplacements, supportRows):
    """Validate one explicitly selected schema2 recipe, entirely before writes.

    baseReplacements must contain only quest-localization rows; the caller keeps
    any separately authorized non-quest replacement checks outside this module.
    """
    if (not isinstance(descriptor, dict) or set(descriptor) != FIELDS or
            type(descriptor.get("schemaVersion")) is not int or descriptor["schemaVersion"] != 2 or descriptor.get("kind") != KIND):
        raise ValueError("Unknown opt-in native locale descriptor")
    if (descriptor["manifestPath"] != MANIFEST or descriptor["patchTool"] != PATCH_TOOL or
            descriptor["patchToolSha256"] != PATCH_SHA):
        raise ValueError("Unreviewed display patch tool/path")
    if digest(upstreamBytes) != descriptor["upstreamLockSha256"]:
        raise ValueError("Dynamic profile differs from exact upstream lock")
    upstream = parse(upstreamBytes)
    if not isinstance(upstream, dict) or type(upstream.get("schemaVersion")) is not int or upstream["schemaVersion"] != 1:
        raise ValueError("Unsupported native author lock")
    identity = upstream.get("pack", {})
    if (not isinstance(identity, dict) or type(identity.get("projectId")) is not int or identity["projectId"] != 715572 or
            type(identity.get("clientFileId")) is not int or identity["clientFileId"] <= 0 or
            not isinstance(identity.get("clientArchiveSha256"), str) or not SHA.fullmatch(identity["clientArchiveSha256"])):
        raise ValueError("Not an exact ATM9 author release identity")
    version = identity.get("version")
    if (not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9._+-]{1,64}", version) or
            descriptor["sourceVersion"] != version):
        raise ValueError("Dynamic profile version differs from native author lock")
    native = [*upstream.get("files", []), *upstream.get("overrides", [])]
    if upstream.get("client"):
        native.append(upstream["client"])
    source = index_rows(native, "native BASE")
    supplied = index_rows(originalRows, "caller BASE")
    if {p: (r["sizeBytes"], r["sha256"]) for p, r in source.items()} != {
            p: (r["sizeBytes"], r["sha256"]) for p, r in supplied.items()}:
        raise ValueError("Caller BASE rows differ from exact upstream bytes")
    supports = index_rows(supportRows, "support")
    if set(source) & set(supports):
        raise ValueError("Support must not shadow a native BASE row")
    role = descriptor["russianRole"]
    expected_role = "base" if RU in source else "support" if RU in supports else "absent"
    if role != expected_role:
        raise ValueError("Russian BASE/support role differs from native input")
    manifest_raw = read_pin(pack, MANIFEST, descriptor["manifestSha256"])
    read_pin(pack, PATCH_TOOL, PATCH_SHA, limit=1024 * 1024)
    profile = parse(manifest_raw)
    if (type(profile.get("schemaVersion")) is not int or profile["schemaVersion"] != 2 or profile.get("kind") != PROFILE_KIND or
            profile.get("sourceVersion") != version):
        raise ValueError("Not a schema2 profile for this exact author version")
    spec = importlib.util.spec_from_file_location("_approved_atm9_display", resource(pack, PATCH_TOOL))
    display = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(display)
    files = display.load_manifest(resource(pack, MANIFEST))
    overlays = {row["path"]: row for row in files}
    replacements = index_rows(baseReplacements, "quest replacement")
    if set(replacements) != set(overlays):
        raise ValueError("Quest replacement/profile path set differs")
    for path, row in overlays.items():
        old = source.get(path)
        new = replacements[path]
        if set(new) != {"path", "originalSha256", "originalSizeBytes", "sha256", "sizeBytes", "kind", "reason"}:
            raise ValueError("Unexpected quest replacement fields")
        if (old is None or new.get("kind") != "quest-localization" or
                row["originalSha256"] != old["sha256"] or row["originalSizeBytes"] != old["sizeBytes"] or
                new.get("originalSha256") != old["sha256"] or new.get("originalSizeBytes") != old["sizeBytes"] or
                row["localizedSha256"] != new["sha256"] or row["localizedSizeBytes"] != new["sizeBytes"]):
            raise ValueError("Quest row is not bound to native BASE and exact profile: " + path)

    original_data, localized_data = {}, {}
    for path, row in overlays.items():
        current = resource(pack, path).read_bytes()
        if digest(current) == row["originalSha256"] and len(current) == row["originalSizeBytes"]:
            before = current
        elif digest(current) == row["localizedSha256"] and len(current) == row["localizedSizeBytes"]:
            before = display.transform(current, row, False)
        else:
            raise ValueError("Unknown physical localized/original resource: " + path)
        original_data[path] = before
        localized_data[path] = display.transform(before, row, True)

    def original(path):
        if path in original_data:
            return original_data[path]
        row = source.get(path)
        if row is None:
            raise ValueError("Missing native locale context: " + path)
        raw = resource(pack, path).read_bytes()
        if len(raw) != row["sizeBytes"] or digest(raw) != row["sha256"]:
            raise ValueError("Unknown native locale context bytes: " + path)
        return raw

    aliases = {}
    legacy_rows = approved_aliases = None

    def legacy_aliases(path, row, value):
        nonlocal legacy_rows, approved_aliases
        if legacy_rows is None:
            legacy = parse(read_pin(pack, "tools/atm9_ru_future/legacy-1.1.1-manifest.json", LEGACY_SHA))
            legacy_rows = {r["path"]: r for r in legacy["files"]}
            approved_aliases = parse(read_pin(pack, "tools/atm9_ru_future/legacy-alias-english.json", ALIASES_SHA))
        if legacy_rows.get(path) != row:
            raise ValueError("Unreviewed source display/component change")
        keys = set(ALIAS_KEY.findall(value))
        if not keys or keys - set(approved_aliases):
            raise ValueError("Unknown reviewed native alias: " + path + " " + value[:180])
        return {key: approved_aliases[key] for key in keys}
    for path, row in overlays.items():
        if path in {EN, RU}:
            continue
        before, after = original_data[path].decode("utf-8"), localized_data[path].decode("utf-8")
        trees = [Snbt(before).parse(), Snbt(after).parse()]
        for edit in row["edits"]:
            trail = edit.get("displayPath")
            field = display_field(trail)
            nodes = [locate(tree, trail) for tree in trees]
            for text, node, state in zip([before, after], nodes, ["original", "localized"]):
                raw = base64.b64decode(edit[state + "Base64"], validate=True)
                if (edit[state + "Offset"] != len(text[:node.start].encode("utf-8")) or
                        raw != text[node.start:node.end].encode("utf-8")):
                    raise ValueError("Claimed display span is not the actual native leaf")
            try:
                used = display_aliases(nodes[0].value, nodes[1].value, field)
            except (ValueError, UnicodeError):
                # A byte-exact already reviewed legacy row may contain the one
                # published brace typo correction; no new row gets this waiver.
                used = legacy_aliases(path, row, nodes[1].value)
            for key, value in used.items():
                if key in aliases and aliases[key][0] != value:
                    raise ValueError("Alias maps distinct native English display values")
                aliases[key] = (value, path, row)
    old_en = new_en = None
    if EN in overlays or aliases or RU in overlays:
        old_en = string_table(original(EN))
        new_en = string_table(localized_data.get(EN, original(EN)))
        if any(new_en.get(k) != v for k, v in old_en.items()):
            raise ValueError("Original English values must remain unchanged")
        added = set(new_en) - set(old_en)
        if added - set(aliases):
            raise ValueError("English additions must be used native display aliases")
        for key, (value, path, row) in aliases.items():
            if new_en.get(key) == value:
                continue
            # The one previously reviewed brace correction stays exact; no
            # general exception can approve a new changed English display.
            legacy = parse(read_pin(pack, "tools/atm9_ru_future/legacy-1.1.1-manifest.json", LEGACY_SHA))
            known = next((r for r in legacy["files"] if r["path"] == path), None)
            approved = parse(read_pin(pack, "tools/atm9_ru_future/legacy-alias-english.json", ALIASES_SHA))
            if known != row or not (key in old_en or approved.get(key) == new_en.get(key)):
                raise ValueError("Alias changes original English display semantics: " + path + " " + key)
    if RU in overlays:
        old_ru, new_ru = string_table(original_data[RU]), string_table(localized_data[RU])
        for key, value in old_ru.items():
            if (key not in old_en or value.strip() and value != old_en[key]) and new_ru.get(key) != value:
                raise ValueError("Native author Russian value was overwritten")
    if role == "support":
        row = supports[RU]
        raw = read_pin(pack, RU, row["sha256"], limit=8 * 1024 * 1024)
        if len(raw) != row["sizeBytes"]:
            raise ValueError("Russian support size differs")
        string_table(raw)
    effective = copy.deepcopy(originalRows)
    for row in effective:
        if row["path"] in replacements:
            new = replacements[row["path"]]
            row.update(sizeBytes=new["sizeBytes"], sha256=new["sha256"])
            row.pop("sha1", None)
    return {"profile": profile, "records": originalRows, "replacements": baseReplacements,
            "effectiveBaseRows": effective, "overlays": overlays, "russianRole": role}
