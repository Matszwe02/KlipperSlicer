# KlipperSlicer
Slicer integration for klipper

- Access your slicer directly from web UI
  - only mainsail supported for now

- Drag & drop stl/stp/3mf directly into your printer

- Don't worry about different slicer versions on different PCs

- Auto update config whenever you slice from external slicer

![alt text](.github/image.png)
![alt text](.github/image2.png)

## Installation

- run `install.sh`
- choose your slicer and if you want to have slicer accessible via mainsail
- edit the newly created config file as per your needs
- If you want to use your own slicer with web ui, choose an app that runs at port **3000 http**
- If you want to use your own slicer without web ui, you can download executable and assign it in configuration file