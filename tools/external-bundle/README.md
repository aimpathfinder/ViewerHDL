# External HDL tool bundle integration

ViewerHDL can use an existing HDL tool directory instead of requiring tools to be installed system-wide. The simplest project layout is to put the bundle beside the HDL sources:

```text
my-project/
  rtl/
    top.sv
    alu.sv
  kianv-tools/
    bin/
      python.exe
      yosys.exe
      dot.exe
      ghdl.exe
    plugins/
      ghdl.dll
```

When HDL files are selected from the desktop viewer, ViewerHDL walks their parent directories and automatically discovers `kianv-tools` or `kianv-toolchain`. No global installation or `PATH` change is needed. The bundle can also be entered manually under **HDL toolchain → External bundle folder**, then saved.

The viewer checks the bundle root and its `bin` subdirectory first, then checks individually configured executable paths, then falls back to `PATH`.

A typical bundle layout is:

```text
my-hdl-tools/
  bin/
    python.exe
    yosys.exe
    dot.exe
    ghdl.exe
  plugins/
    ghdl.so        # Linux/macOS example
    ghdl.dll       # Windows/MSYS2 example, if supplied by the bundle
```

If the executable names or plugin location differ, configure the individual fields in the viewer:

- Python executable
- Yosys executable
- GHDL executable
- Graphviz `dot` executable
- GHDL-Yosys plugin folder

The viewer stores these settings in the Electron user-data directory. It does not modify the system `PATH`.

The bundle itself is intentionally a configuration template, not a redistribution of third-party binaries. Users may point it at an existing OSS CAD Suite, MSYS2 EDA installation, WSL-mounted tool directory, or another legally redistributable HDL tool bundle.
