# 1. KlipperSlicer - about
 PrusaSlicer / Superslicer / Slic3r integration for klipper


# 2. Usage
- Upload `.stl` files anywhere inside `printer_data` folder.
Default slicer is set to `PrusaSlicer 2.6.1`. You can change it in `~/KlipperSlicer/slicer_data/slicer/`.

- 3d printer config will be automatically generated and updated everytime a `.gcode` is uploaded into `printer_data/gcodes`. Config file is stored in `~/KlipperSlicer/slicer_data/config.ini`.

- You can start preheating your printer using `_SLICING_PREHEAT EXTRUDER=... BED=...` macro.
  
    Example:
    ```
    [gcode_macro _SLICING_PREHEAT]
    gcode:
        {% if printer.idle_timeout.state != "Printing" %}
            SET_HEATER_TEMPERATURE HEATER=extruder TARGET={params.EXTRUDER|default(0)|int}
            SET_HEATER_TEMPERATURE HEATER=heater_bed TARGET={params.BED|default(0)|int}
        {% endif %}
    ```


# 3. Moonraker.conf
```
[update_manager KlipperSlicer]
type: git_repo
primary_branch: main
path: ~/KlipperSlicer
origin: https://github.com/Matszwe02/KlipperSlicer.git
install_script: scripts/install.sh
managed_services: KlipperSlicer
```