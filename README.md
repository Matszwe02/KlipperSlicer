# 1. KlipperSlicer - about
 PrusaSlicer / Superslicer / Slic3r integration for klipper


# 2. Usage
Upload `.stl` files anywhere inside `printer_data` folder.
Default slicer is set to `PrusaSlicer 2.6.0`. You can change it in `~/KlipperSlicer/slicer_data/slicer/`.

3d printer config will be automatically generated and updated everytime a `.gcode` is uploaded into `printer_data/gcodes`. Config file is stored in `~/KlipperSlicer/slicer_data/config.ini`.


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