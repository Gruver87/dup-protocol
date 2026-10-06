#!/usr/bin/env python3
"""Critical-path pattern scan (honesty tool — not a green paint / not soak).

Exit 0 always; prints findings for operator triage. Prefer industrial_gate +
mesh probe for L1 acceptance.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP = {
    "abs_native/target",
    ".git",
    "node_modules",
    "__pycache__",
    "data",
    "logs",
    ".venv",
    "venv",
    "pack",
    "docs/evidence",
}
CRIT = (
    "consensus",
    "crypto",
    "storage",
    "network",
    "sync",
    "bridge",
    "runtime",
    "api",
    "core",
    "features",
    "execution",
)


def skip_rel(rel: str) -> bool:
    r = rel.replace("\\", "/")
    return any(s in r for s in SKIP)


def main() -> None:
    findings: dict[str, list[str]] = {}

    def add(kind: str, msg: str) -> None:
        findings.setdefault(kind, []).append(msg)

    for p in ROOT.rglob("*.py"):
        rel = p.as_posix().replace(str(ROOT).replace("\\", "/") + "/", "")
        if not rel.startswith(tuple(c + "/" for c in CRIT)) and not any(
            rel.startswith(c + "/") for c in CRIT
        ):
            # also scan sdk
            if not rel.startswith("sdk/"):
                continue
        if skip_rel(rel):
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            code = line.split("#")[0]
            if "verify=False" in code or "verify = False" in code:
                add("tls_verify_false", f"{rel}:{i}: {line.strip()[:100]}")
            if re.search(r"allow_float_fallback\s*=\s*True", code):
                add("money_float_fallback_true", f"{rel}:{i}: {line.strip()[:100]}")
            if re.search(
                r"(SECRET|PASSWORD|API_KEY|JWT_SECRET)\s*=\s*[\"'][^\"']{8,}",
                code,
            ):
                if "example" not in rel.lower() and "test" not in rel.lower():
                    add(
                        "possible_hardcoded_secret",
                        f"{rel}:{i}: {line.strip()[:80]}",
                    )

    for base in ("config", "configs", "docker", "deploy"):
        b = ROOT / base
        if not b.exists():
            continue
        for p in b.rglob("*.json"):
            rel = p.as_posix()
            if "example" in rel.lower() or "lab" in rel.lower() or "bridge" in rel.lower():
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
            for flag in (
                "feature_long_range",
                "feature_nft",
                "feature_libp2p",
                "feature_ai_agents",
                "bridge_enabled",
            ):
                m = re.search(rf'"{flag}"\s*:\s*true', text, re.I)
                if m:
                    line = text.count("\n", 0, m.start()) + 1
                    add("prod_feature_true", f"{rel}:{line}: {flag}=true")

    print("=== CRITICAL SCAN SUMMARY ===")
    if not findings:
        print("No automated P0 pattern hits.")
    for kind, items in sorted(findings.items()):
        print(f"\n[{kind}] n={len(items)}")
        for x in items[:40]:
            print(" ", x)
        if len(items) > 40:
            print(f"  ... +{len(items) - 40} more")


if __name__ == "__main__":
    main()
