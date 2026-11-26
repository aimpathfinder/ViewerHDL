#!/usr/bin/env python3
"""Render any synthesizable Verilog module as a standalone logical schematic.

The tool parses every module first, infers top-level candidates from module
instantiation relationships, then lets the user render either an inferred top
or any non-top module independently.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise SystemExit(f"Required executable not found: {cmd[0]}") from exc


def parse_design(files: list[Path]) -> dict:
    """Parse without choosing a top, preserving every module definition."""
    script = "read_verilog -sv " + " ".join(f'"{f}"' for f in files) + ";"
    tmp = files[0].parent / ".module-viewer-discovery.json"
    result = run(["yosys", "-q", "-p", script + f' write_json "{tmp}"'])
    if result.returncode != 0 or not tmp.exists():
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit("Yosys could not parse the Verilog input.")
    try:
        return json.loads(tmp.read_text())
    finally:
        tmp.unlink(missing_ok=True)


def parse_vhdl_hierarchy(files: list[Path]) -> tuple[list[str], list[str]]:
    """Discover VHDL entities and entity/component references for top inference."""
    text = "\n".join(f.read_text(errors="ignore") for f in files)
    entities = sorted(set(re.findall(r"\bentity\s+([A-Za-z_][\w]*)\s+is\b", text, re.I)))
    refs = set(re.findall(r"\bentity\s+work\.([A-Za-z_][\w]*)", text, re.I))
    refs.update(re.findall(r"\bcomponent\s+([A-Za-z_][\w]*)\s+is\b", text, re.I))
    lowered = {name.lower(): name for name in entities}
    instantiated = {lowered[r.lower()] for r in refs if r.lower() in lowered}
    return entities, sorted(set(entities) - instantiated)


def hierarchy_info(data: dict) -> tuple[list[str], list[str]]:
    modules = data.get("modules", {})
    names = sorted(modules)
    defined = set(names)
    instantiated: set[str] = set()
    for module in modules.values():
        for cell in module.get("cells", {}).values():
            cell_type = cell.get("type", "")
            if cell_type in defined and cell_type != module:
                instantiated.add(cell_type)
    tops = sorted(defined - instantiated)
    return names, tops


def render(files: list[Path], module: str, output: Path, keep_intermediate: bool, tops: list[str], language: str) -> None:
    output.mkdir(parents=True, exist_ok=True)
    safe_name = module.replace("/", "_").replace("\\", "_")
    json_path = output / f"{safe_name}.json"
    svg_prefix = output / safe_name
    quoted_files = " ".join(f'"{f}"' for f in files)
    vhdl_files = " ".join(str(f) for f in files)
    if language == "vhdl":
        script = f"""
          ghdl --std=08 {vhdl_files} -e {module}
          proc
          opt
          check
          write_json "{json_path}"
          show -format svg -prefix {svg_prefix} -notitle {module}
        """
        command = ["yosys", "-m", "ghdl", "-p", script]
    else:
        script = f"""
          read_verilog -sv {quoted_files}
          hierarchy -top {module}
          proc
          opt
          check
          write_json "{json_path}"
          show -format svg -prefix {svg_prefix} -notitle {module}
        """
        command = ["yosys", "-p", script]
    result = run(command)
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Yosys could not render module {module!r}.")
    svg_path = output / f"{safe_name}.svg"
    dot_path = output / f"{safe_name}.dot"
    if not svg_path.exists():
        candidates = list(output.glob(f"{safe_name}*.svg"))
        if candidates:
            candidates[0].rename(svg_path)
    metadata = {
        "module": module,
        "inferred_top_candidates": tops,
        "inputs": [str(f) for f in files],
        "json": str(json_path),
        "svg": str(svg_path),
        "mode": "standalone module view",
        "language": language,
        "technology": "technology-independent logical schematic",
        "physical_layout": False,
    }
    (output / f"{safe_name}.meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if not keep_intermediate:
        dot_path.unlink(missing_ok=True)
    print(f"module: {module}")
    print(f"SVG schematic: {svg_path}")
    print(f"JSON netlist:  {json_path}")
    print("technology:    independent logical view (not GDS/OASIS)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Verilog/SystemVerilog source files")
    parser.add_argument("--module", help="module to render; defaults to the unique inferred top")
    parser.add_argument("--top", help="explicit top candidate to report/select when multiple exist")
    parser.add_argument("--output", type=Path, default=Path("module-view"), help="output directory")
    parser.add_argument("--list-modules", action="store_true", help="list modules and inferred top candidates")
    parser.add_argument("--keep-intermediate", action="store_true", help="keep Graphviz DOT output")
    parser.add_argument("--vhdl", action="store_true", help="read VHDL files through GHDL-Yosys")
    args = parser.parse_args()

    language = "vhdl" if args.vhdl else "verilog"
    if args.vhdl and (shutil.which("ghdl") is None or shutil.which("yosys") is None):
        raise SystemExit("VHDL mode requires both GHDL and Yosys.")
    files = [f.resolve() for f in args.files]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise SystemExit("Input file(s) not found: " + ", ".join(missing))
    if shutil.which("yosys") is None or shutil.which("dot") is None:
        raise SystemExit("This tool requires both yosys and graphviz (dot).")
    if language == "vhdl":
        modules, tops = parse_vhdl_hierarchy(files)
    else:
        data = parse_design(files)
        modules, tops = hierarchy_info(data)
    if args.top and args.top not in tops:
        raise SystemExit(f"--top {args.top!r} is not an inferred top candidate: {', '.join(tops) or '(none)'}")
    print("Inferred top-level candidates:")
    for name in tops:
        print(f"  {name}")
    print("Parsed modules:")
    for name in modules:
        marker = " [top candidate]" if name in tops else ""
        print(f"  {name}{marker}")
    if args.list_modules:
        return 0

    selected = args.module
    if selected is None:
        if args.top:
            selected = args.top
        elif len(tops) == 1:
            selected = tops[0]
        else:
            raise SystemExit("Multiple or no top candidates found; choose --module or --top explicitly.")
    if selected not in modules:
        raise SystemExit(f"Unknown module {selected!r}. Use --list-modules first.")
    render(files, selected, args.output, args.keep_intermediate, tops, language)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
