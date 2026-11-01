"""Restore only the pack's two owned client scripts and validate public native APIs.

This is source preparation, never a launcher hook or a personal-config writer.
Unchanged public APIs allow later author JAR versions; changed APIs require review.
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import zipfile

HERE = Path(__file__).resolve().parent


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def target(root, relative):
    require(isinstance(relative, str) and relative and "\\" not in relative and ":" not in relative
            and all(p not in {"", ".", ".."} for p in relative.split("/")), "Unsafe owned path")
    p = root
    for part in relative.split("/"):
        p /= part
        require(not p.is_symlink() and not (hasattr(p, "is_junction") and p.is_junction()), "Linked owned path")
    require(p.resolve().is_relative_to(root.resolve()), "Owned path escaped pack")
    return p


def class_members(data):
    require(data[:4] == b"\xca\xfe\xba\xbe", "Not a JVM class")
    pos, index, count = 10, 1, struct.unpack_from(">H", data, 8)[0]
    pool = [None] * count
    while index < count:
        tag = data[pos]
        pos += 1
        if tag == 1:
            length = struct.unpack_from(">H", data, pos)[0]
            pos += 2
            pool[index] = data[pos:pos+length].decode("utf-8", "replace")
            pos += length
        elif tag in {7, 8, 16, 19, 20}:
            pos += 2
        elif tag in {3, 4, 9, 10, 11, 12, 17, 18}:
            pos += 4
        elif tag in {5, 6}:
            pos += 8
            index += 1
        elif tag == 15:
            pos += 3
        else:
            raise ValueError("Unknown JVM constant tag")
        index += 1
    flags, _, _, interfaces = struct.unpack_from(">HHHH", data, pos)
    pos += 8 + interfaces * 2
    groups = []
    for _ in range(2):
        size = struct.unpack_from(">H", data, pos)[0]
        pos += 2
        rows = []
        for _ in range(size):
            access, name, descriptor, attributes = struct.unpack_from(">HHHH", data, pos)
            pos += 8
            rows.append({"flags": access, "name": pool[name], "descriptor": pool[descriptor]})
            for _ in range(attributes):
                length = struct.unpack_from(">I", data, pos + 2)[0]
                pos += 6 + length
        groups.append(rows)
    return {"flags": flags, "fields": groups[0], "methods": groups[1]}


def check_contract(contract, data):
    native = class_members(data)
    require(native["flags"] & 1, "Native class is no longer public: " + contract["class"])
    for group in ("fields", "methods"):
        for expected in contract.get(group, []):
            rows = [row for row in native[group] if row["name"] == expected["name"]
                    and row["descriptor"] == expected["descriptor"]]
            require(len(rows) == 1, "Native member missing/changed: " + contract["class"] + "." + expected["name"])
            flags = rows[0]["flags"]
            require(flags & 1 and bool(flags & 8) == expected["static"], "Native member access/static changed")
            if group == "fields":
                require(not flags & 16, "Native setting is no longer mutable")


def verify_apis(pack, policy):
    wanted = {row["class"] + ".class": row for row in policy["apiContracts"]}
    providers = {}
    for jar in sorted((pack / "mods").glob("*.jar")):
        require(not jar.is_symlink(), "Linked mod JAR")
        with zipfile.ZipFile(jar) as archive:
            for name in wanted.keys() & set(archive.namelist()):
                require(name not in providers, "Duplicate native API provider: " + name)
                data = archive.read(name)
                check_contract(wanted[name], data)
                providers[name] = {"class": name, "fileName": jar.name,
                                   "jarSha256": digest(jar.read_bytes()), "classSha256": digest(data)}
    require(set(providers) == set(wanted), "Required native client-policy API is absent")
    return sorted(providers.values(), key=lambda row: row["class"])


def prepare_outputs(pack, tool, policy, apply=False):
    pending = []
    for row in policy["scripts"]:
        path = target(pack, row["path"])
        template = target(tool, row["template"]).read_bytes()
        require(len(template) == row["sizeBytes"] and digest(template) == row["sha256"], "Owned template pin differs")
        if path.exists():
            require(path.is_file() and path.read_bytes() == template, "Conflicting source script; review instead of overwrite: " + row["path"])
        else:
            require(apply, "Owned client script is absent: " + row["path"])
            pending.append((path, template))
    # Validate all source outputs before writing any of them.
    for path, raw in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return len(pending)


def prepare(pack, apply=False, templates_only=False):
    pack = Path(pack).resolve()
    tool = pack / "tools/client-policy"
    policy = json.loads((tool / "policy.json").read_text(encoding="utf-8"))
    require(policy["schemaVersion"] == 1 and policy["kind"] == "pack-owned-native-client-policy", "Unsupported client policy")
    require(not templates_only or apply, "Templates-only preparation requires --apply")
    providers = [] if templates_only else verify_apis(pack, policy)
    restored = prepare_outputs(pack, tool, policy, apply)
    if templates_only:
        return {"status": "SOURCE_SCRIPTS_READY_NATIVE_API_NOT_CHECKED",
                "scope": "Hash-pinned owned source templates only; author JAR restoration/native API validation is still required",
                "restoredOwnedScripts": restored, "scripts": policy["scripts"],
                "nativeApiValidated": False, "personalConfigFilesTouched": False, "gameJarsChanged": False}
    return {"status": "PASS", "scope": "Native public API and exact source-script preparation; no runtime or visual acceptance",
            "restoredOwnedScripts": restored, "scripts": policy["scripts"], "nativeApis": providers,
            "personalConfigFilesTouched": False, "gameJarsChanged": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=HERE.parents[1])
    parser.add_argument("--apply", action="store_true", help="Restore missing owned source scripts only")
    parser.add_argument("--templates-only", action="store_true", help="With --apply, restore source templates before omitted author JARs; no native API acceptance")
    args = parser.parse_args()
    print(json.dumps(prepare(args.pack, args.apply, args.templates_only), indent=2))


if __name__ == "__main__":
    main()
