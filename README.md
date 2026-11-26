# ViewerHDL

ViewerHDL is an interactive logical and generic-CMOS viewer for synthesizable Verilog/SystemVerilog and VHDL projects.

## What it does

- Imports multi-file Verilog/SystemVerilog or VHDL projects in the Windows desktop app.
- Infers top-level candidates and exposes non-top modules for independent viewing.
- Draws synthesized connectivity as outlined logical components such as AND, OR, NAND, NOR, XOR, and NOT.
- Expands selected generic gates into illustrative CMOS topologies with explicit NMOS/PMOS devices and Source/Gate/Drain terminals.
- Preserves the bundled CPU and module artifacts, including whole-design transistor-oriented views and user-controlled layouts.
- Detects tools from a project-local `kianv-tools` directory, configured executable paths, or `PATH`.

The viewer is a technology-independent logical/CMOS abstraction. It is not a physical transistor extraction tool and does not produce manufacturable GDS/OASIS layout.

## Desktop package

Download the portable Windows package from the Releases page. Extract the ZIP and run `ViewerHDL.exe` from the extracted folder.

For arbitrary HDL import, use **Import HDL project**. The desktop machine needs Python, Yosys, Graphviz `dot`, and—when importing VHDL—GHDL plus the GHDL-Yosys plugin. Tools can be supplied in a project-local `kianv-tools/bin` directory or configured in the app's **HDL toolchain** panel. See [`tools/external-bundle/README.md`](tools/external-bundle/README.md).

## CLI

```bash
python3 tools/module_viewer.py rtl/*.v --list-modules
python3 tools/module_viewer.py rtl/*.v --module alu --output module-view/alu
python3 tools/module_viewer.py --vhdl rtl/*.vhd --module alu --output module-view/alu
```

## Development

```bash
pnpm install
pnpm run build
pnpm run desktop:build
```

The Windows portable build uses Electron. The Linux build environment may produce the Windows unpacked payload and portable ZIP but cannot execute the NSIS compiler.

## License

MIT. See [`LICENSE`](LICENSE).
