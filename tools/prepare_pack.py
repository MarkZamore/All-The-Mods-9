#!/usr/bin/env python3
"""Restore exact author ATM9, then reapply its fixed Russian display overlay."""
from pathlib import Path
import argparse
import json
import subprocess
import sys

import portable_profile as profile_tools


def prepare(pack, cache, workers=8, restore_locked_files=False):
    pack = profile_tools.working_root(pack)
    cache = cache.resolve()
    if sys.platform == "win32" and not str(cache).startswith("\\\\?\\"):
        cache = Path("\\\\?\\" + str(cache))
    profile = profile_tools.load(pack)
    if profile is None:
        raise ValueError("The fixed original ATM9 portable profile is missing")
    dynamic = profile.get("dynamic") is not None
    before = profile_tools.preflight(pack, profile, require_overrides=restore_locked_files or dynamic)

    def overlay(mode):
        # Recheck physical pins at each executable boundary, not just on entry.
        current = profile_tools.load(pack)
        descriptor = current["document"]["questLocalization"] if dynamic else None
        tool = descriptor["patchTool"] if descriptor else "tools/atm9_ru_quests.py"
        manifest = descriptor["manifestPath"] if descriptor else "tools/atm9_ru_quests/manifest.json"
        subprocess.run([sys.executable, "-B", str(pack / tool), mode,
                        "--root", str(pack), "--manifest", str(pack / manifest)], check=True)

    overlay("normalize")
    current = profile_tools.load(pack)
    if dynamic:
        import atm9_quest_restore
        atm9_quest_restore.restore_profiled_author(pack, cache, current["document"]["questLocalization"],
                                                   current["upstreamBytes"], current["records"])
    else:
        command = [sys.executable, "-B", str(pack / "tools/import_upstream.py"),
                   "--pack", str(pack), "--cache", str(cache), "--workers", str(workers)]
        if restore_locked_files:
            command.append("--restore-locked-files")
        subprocess.run(command, check=True)
    profile_tools.preflight(pack, profile_tools.load(pack), require_all=True, original_only=True)
    overlay("apply")
    final = profile_tools.preflight(pack, profile_tools.load(pack), require_all=True, localized_only=True)
    overlay("verify")
    return {"status": "PASS", "authorVersion": profile["document"]["sourceVersion"] if dynamic else "1.1.1", "before": before, "effective": final}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--restore-locked-files", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be between 1 and 16")
    cache = (args.cache or args.pack / "artifacts/upstream").resolve()
    try:
        print(json.dumps(prepare(args.pack, cache, args.workers, args.restore_locked_files), sort_keys=True))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as exception:
        parser.exit(1, "Original ATM9 preparation failed: " + str(exception) + "\n")


if __name__ == "__main__":
    main()
