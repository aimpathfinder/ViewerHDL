#!/usr/bin/env python3
"""Render any synthesizable Verilog module as a standalone logical schematic.

This intentionally does not flatten the selected module. The selected module is
made the temporary Yosys top so it can be viewed independently of the chip top.
Child modules remain hierarchical cells when their definitions are available.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise SystemExit(f"Required executable not found: {cmd[0]}") from exc


def discover_modules(files: list[Path]) -> list[str]:
    # Read without selecting a top so every module definition remains available.
    script = "read_verilog -sv " + " ".join(f'"{f}"' for f in files) + ";"
    result = run(["yosys", "-q", "-p", script])
    if result.returncode != 0:
        print(result.stderr or result.stdout, file=sys.stderr)
        raise SystemExit("Yosys could not parse the Verilog input.")
    # A JSON dump gives an authoritative module list without scraping logs.
    tmp = files[0].parent / ".module-viewer-discovery.json"
    result = run(["yosys", "-q", "-p", script + f' write_json "{tmp}"'])
    if result.returncode != 0 or not tmp.exists():
        raise SystemExit(result.stderr or "Yosys did not produce a discovery netlist.")
    try:
        data = json.loads(tmp.read_text())
        return sorted(data.get("modules", {}).keys())
    finally:
        tmp.unlink(missing_ok=True)


def render(files: list[Path], module: str, output: Path, keep_intermediate: bool) -> None:
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{module}.json"
    svg_prefix = output / module
    quoted_files = " ".join(f'"{f}"' for f in files)
    script = f"""
      read_verilog -sv {quoted_files}
      hierarchy -top {module}
      proc
      opt
      check
      write_json "{json_path}"
      show -format svg -prefix {svg_prefix} -notitle {module}
    """
    result = run(["yosys", "-p", script])
    if result.returncode != 0:
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        raise SystemExit(f"Yosys could not render module {module!r}.")
    svg_path = output / f"{module}.svg"
    dot_path = output / f"{module}.dot"
    # Yosys/Graphviz may use a .svg extension directly; normalize if needed.
    generated = output / f"{module}.svg"
    if not generated.exists():
        candidates = list(output.glob(f"{module}*.svg"))
        if candidates:
            candidates[0].rename(generated)
    metadata = {
        "module": module,
        "inputs": [str(f) for f in files],
        "json": str(json_path),
        "svg": str(svg_path),
        "mode": "standalone module view",
        "technology": "technology-independent logical schematic",
        "physical_layout": False,
    }
    (output / f"{module}.meta.json").write_text(json.dumps(metadata, indent=2) + "\n")
    if not keep_intermediate:
        dot_path.unlink(missing_ok=True)
    print(f"module: {module}")
    print(f"SVG schematic: {svg_path}")
    print(f"JSON netlist:  {json_path}")
    print("technology:    independent logical view (not GDS/OASIS)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+", type=Path, help="Verilog/SystemVerilog source files")
    parser.add_argument("--module", help="module to render; omit with --list-modules")
    parser.add_argument("--output", type=Path, default=Path("module-view"), help="output directory")
    parser.add_argument("--list-modules", action="store_true", help="list all parsed modules and exit")
    parser.add_argument("--keep-intermediate", action="store_true", help="keep Graphviz DOT output")
    parser.add_argument("--vhdl", action="store_true", help="request VHDL mode and check for GHDL")
    args = parser.parse_args()

    if args.vhdl:
        if shutil.which("ghdl") is None:
            raise SystemExit("VHDL mode requires GHDL plus the GHDL-Yosys plugin; ghdl is not installed.")
        raise SystemExit("GHDL-Yosys is detected, but VHDL command integration is not configured in this build yet.")
    files = [f.resolve() for f in args.files]
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise SystemExit("Input file(s) not found: " + ", ".join(missing))
    if shutil.which("yosys") is None or shutil.which("dot") is None:
        raise SystemExit("This tool requires both yosys and graphviz (dot).")
    modules = discover_modules(files)
    if args.list_modules or not args.module:
        print("Parsed modules:")
        for name in modules:
            print(f"  {name}")
        if not args.module:
            return 0
    if args.module not in modules:
        raise SystemExit(f"Unknown module {args.module!r}. Use --list-modules first.")
    render(files, args.module, args.output, args.keep_intermediate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
