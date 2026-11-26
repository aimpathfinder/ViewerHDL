# KianV Netlist Viewer

- [x] Load and select the verified KianV CPU and module netlists from the project artifacts.
- [x] Display a searchable, pannable, zoomable gate-level connectivity graph with cell and net selection.
- [x] Support searching modules, cells, ports, nets, and signal names, with selected-node details and fan-in/fan-out.
- [x] Navigate the available synthesized hierarchy and clearly mark flattened netlists where logical RTL boundaries are not preserved.
- [x] Provide an NMOS/PMOS expansion view for supported generic gates and selected SKY130 library mappings, with the physical-accuracy boundary stated in the UI.
- [x] Emit whole-CPU and per-module hierarchical transistor-oriented JSON artifacts with explicit MOS devices for supported gates and status markers for sequential or unresolved macros.
- [x] Clearly distinguish full CPU/module gate-level graphs from transistor-level detail for an individual standard cell.
- [x] Show metadata including top module, cell count, port count, technology library, and source artifact.
- [x] Verify the viewer against at least the CPU and ALU artifacts and run build/HTTP checks before delivery.
- [x] Provide a standalone Yosys module viewer that lists every parsed Verilog module and exports SVG/JSON for a selected non-top module without GDS/OASIS.
- [ ] Add the GHDL-Yosys front end when GHDL and its Yosys plugin are installed, reusing the same module-only SVG/JSON export path for synthesizable VHDL.
