#!/usr/bin/env python3
"""Check registry.yaml before any refresh runs.

Usage:  pip install pyyaml
        python validate_registry.py registry.yaml

Exit code 0 = no errors (warnings are fine); 1 = errors found.
"""
import re
import sys
import yaml

REQUIRED = ["id", "label", "role", "unit", "status", "source", "update_mode",
            "cadence", "stale_after_days", "licence", "validation", "model", "reader_mapping"]
STATUS = {"baseline_frozen", "found", "to_identify", "blocked"}
ROLE = {"evidence", "context"}
MODE = {"auto", "review", "manual"}


def main(path):
    reg = yaml.safe_load(open(path, encoding="utf-8"))
    errors, warnings, seen = [], [], set()
    ids = {v.get("id") for v in reg.get("variables", [])}

    for v in reg.get("variables", []):
        vid = v.get("id", "<no id>")
        for k in REQUIRED:
            if k not in v:
                errors.append(f"{vid}: missing field '{k}'")
        if vid in seen:
            errors.append(f"{vid}: duplicate id")
        seen.add(vid)
        if v.get("status") not in STATUS:
            errors.append(f"{vid}: status must be one of {sorted(STATUS)}")
        if v.get("role") not in ROLE:
            errors.append(f"{vid}: role must be one of {sorted(ROLE)}")
        if v.get("update_mode") not in MODE:
            errors.append(f"{vid}: update_mode must be one of {sorted(MODE)}")

        src = v.get("source") or {}
        url = src.get("url")
        if v.get("update_mode") == "auto":
            if not url:
                errors.append(f"{vid}: auto variable has no source url")
            if v.get("stale_after_days") is None:
                errors.append(f"{vid}: auto variable needs stale_after_days")
            val = v.get("validation") or {}
            if "min" not in val or "max" not in val:
                errors.append(f"{vid}: auto variable needs validation min and max")
        if v.get("status") == "baseline_frozen" and "baseline" not in v:
            errors.append(f"{vid}: baseline_frozen but no 'baseline' block")
        for dep in v.get("depends_on", []) or []:
            if dep not in ids:
                errors.append(f"{vid}: depends_on unknown id '{dep}'")

        # secrets must be placeholders, never literal keys
        text = yaml.dump(v)
        if re.search(r"api_key=(?!\$\{)[A-Za-z0-9]{16,}", text):
            errors.append(f"{vid}: looks like a literal API key; use ${{NAME}}")

        # warnings: things that are allowed but not ready
        if v.get("status") in {"found", "to_identify"}:
            warnings.append(f"{vid}: status '{v['status']}' (source path not yet tested)")
        m = v.get("model")
        if isinstance(m, dict) and any(m.get(k, 1) is None for k in ("continuation", "acceleration", "reversal")):
            warnings.append(f"{vid}: scenario parameters not set")
        if v.get("status") == "blocked":
            warnings.append(f"{vid}: blocked")

    print(f"{len(reg.get('variables', []))} variables checked")
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("ERROR:  ", e)
    print(f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "registry.yaml"))
