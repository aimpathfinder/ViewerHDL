# Standalone Verilog module viewer

`module_viewer.py` uses Yosys and Graphviz to render a **logical schematic for any selected module**, including modules that are not the chip top level. The selected module becomes a temporary Yosys top only for the export; it is not required to be the project’s CPU top, and child instances remain visible when their definitions are available.

```bash
# List every module found in one or more source files
python3 tools/module_viewer.py rtl/*.v --list-modules

# Render one module without rendering the complete chip
python3 tools/module_viewer.py rtl/*.v --module alu --output module-view/alu
```

The output contains:

- `<module>.svg` — logical schematic image
- `<module>.json` — Yosys structural netlist
- `<module>.meta.json` — provenance and fidelity metadata

This output is technology-independent and does not require GDS/OASIS. It shows the hardware implied by synthesizable structural/RTL Verilog after Yosys has parsed and normalized it. It is not a physical layout and does not invent capacitors or process geometry.

VHDL support is intentionally explicit: the command accepts `--vhdl` only when GHDL is installed, and currently reports that GHDL-Yosys integration must be configured. The next extension is to invoke the GHDL-Yosys front end, then feed its RTLIL into the same module-list and SVG export path.
