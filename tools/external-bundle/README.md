# External HDL tool bundle integration

KianV can use an existing HDL tool directory instead of requiring tools to be installed system-wide. In the desktop viewer, enter the bundle folder under **HDL toolchain → External bundle folder**, then click **Save tool settings**.

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
