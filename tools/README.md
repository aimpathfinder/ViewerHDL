# Standalone Verilog module viewer

`module_viewer.py` uses Yosys/Graphviz for Verilog and the GHDL-Yosys plugin for VHDL to render a **logical schematic for any selected module**, including modules that are not the chip top level. It first parses every module/entity, infers top-level candidates by subtracting instantiated module types from defined module types, and reports the hierarchy. The selected module becomes a temporary Yosys top only for the export; it is not required to be an inferred top, and child instances remain visible when their definitions are available.

```bash
# List every module found in one or more source files
python3 tools/module_viewer.py rtl/*.v --list-modules

# Render one module without rendering the complete chip
python3 tools/module_viewer.py rtl/*.v --module alu --output module-view/alu

# If exactly one top-level candidate exists, render it automatically
python3 tools/module_viewer.py rtl/*.v --output module-view/top

# VHDL through GHDL-Yosys
python3 tools/module_viewer.py --vhdl rtl/*.vhd --list-modules
python3 tools/module_viewer.py --vhdl rtl/*.vhd --module alu --output module-view/alu
```

The output contains:

- `<module>.svg` — logical schematic image
- `<module>.json` — Yosys structural netlist
- `<module>.meta.json` — provenance and fidelity metadata

This output is technology-independent and does not require GDS/OASIS. It shows the hardware implied by synthesizable structural/RTL Verilog after Yosys has parsed and normalized it. It is not a physical layout and does not invent capacitors or process geometry.

VHDL support uses the installed `ghdl` executable and `yosys-plugin-ghdl`. Entity names and entity/component references are used for top-level reporting; the selected entity is then imported by GHDL-Yosys and passed through the same logical SVG/JSON export path.
