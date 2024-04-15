import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import os
from datetime import datetime


last_file_change = datetime.now().timestamp()
user = os.listdir('/home')[0]

gcode_console = f"/home/{user}/printer_data/comms/klippy.serial"
slicer_exec = "None"
config_file = f"/home/{user}/KlipperSlicer/slicer_data/config.ini"
temp_gcode = f"/home/{user}/KlipperSlicer/slicer_data/gcodes/"
gcodes_dir = f'/home/{user}/printer_data/gcodes/'

orca_slicer_repo = 'https://github.com/SoftFever/OrcaSlicer/releases/download/v{VERSION}/OrcaSlicer_Linux_V{VERSION}.AppImage'
prusa_slicer_repo = 'https://github.com/prusa3d/PrusaSlicer/releases/download/version_2.7.4/PrusaSlicer-2.7.4+linux-armv7l-GTK2-202404050928.AppImage' # TODO: implement versioning
super_slicer_repo = 'https://github.com/supermerill/SuperSlicer/releases/download/{VERSION}/SuperSlicer-ubuntu_18.04-{VERSION}.AppImage' #TODO: test


token = False

for path in ['./slicer_data', './slicer_data/gcodes', './slicer_data/slicer']:
    os.makedirs(path, exist_ok=True)


def set_slicer(name: str):
    
    global slicer_exec
    
    name = name.strip()
    split_index = name.replace('_', ' ').replace('+', ' ').index(' ')
    version = name[split_index :].strip()
    name = name[: split_index].strip()
    
    msg(f'Found Slicer {name} version {version}')
    
    slicer_present = False
    for file in os.listdir("./slicer_data/slicer/"):
        if name.lower() in file.lower():
            slicer_present = True
        else:
            try:
                os.remove("./slicer_data/slicer/" + file)
            except PermissionError:
                os.system(f'sudo rm ./slicer_data/slicer/{file}')
            print('ok')
    
    if not slicer_present:
        if name.lower() == 'orcaslicer':
            msg(f'Downloading OrcaSlicer {version} ...')
            os.system(f'wget -P ./slicer_data/slicer/ {orca_slicer_repo.replace("{VERSION}", version)}')
        elif name.lower() == 'prusaslicer':
            msg(f'Downloading PrusaSlicer 2.7.4 (other versions needed to be added manually) ...')
            os.system(f'wget -P ./slicer_data/slicer/ {prusa_slicer_repo.replace("{VERSION}", version)}')
        elif name.lower() == 'superslicer':
            msg(f'Downloading SuperSlicer {version} ...')
            os.system(f'wget -P ./slicer_data/slicer/ {super_slicer_repo.replace("{VERSION}", version)}')
        else:
            msg('Could not find selected slicer', True)
            raise NotImplementedError
    
    slicer_exec = (os.listdir("./slicer_data/slicer/"))[0]
    os.system(f"chmod a+x ./slicer_data/slicer/{slicer_exec}")
    


def run_gcode(command):
    with open(gcode_console, 'a') as console:
        console.write(command + '\n')


def msg(message, is_error = False):
    addon = ''
    if is_error: addon = "TYPE=error "
    run_gcode(f"RESPOND {addon}MSG=\"Slicer: {message}\"")
    print(f"{message}")


def file_wait_for_download(filename):
        file_size = -1
        while file_size != os.path.getsize(filename):
            file_size = os.path.getsize(filename)
            time.sleep(2)


class FileChangeEvent(LoggingEventHandler):        
    def on_created(self, event):
        global token
        while token: time.sleep(10000)
        token = True
        
        try:
            global last_file_change
            file = event.src_path
            
            if datetime.now().timestamp() - last_file_change < 5: return
            
            if file[-4:].lower() == '.stl':
                if not os.path.exists(config_file):
                    msg('Config.ini missing. Upload any gcode to initialize config file!', True)
                    os.remove(file)
                    return
                file_gcode = (os.path.basename(file)[:-4] + '.gcode').replace(" ", "_")
                msg('Slicing file...')
                with open(config_file, 'r') as config:
                    lines = config.readlines()
                    e_temp = 0
                    b_temp = 0
                    for line in lines:
                        if line.startswith('first_layer_temperature = '):
                            e_temp = int(line[26:])
                        if line.startswith('first_layer_bed_temperature = '):
                            b_temp = int(line[30:])
                    
                    run_gcode(f"_SLICING_PREHEAT EXTRUDER={e_temp} BED={b_temp}")
                            
                output = 256
                tries = 0
                file_wait_for_download(file)
                while output == 256 and tries < 600:
                    time.sleep(1)
                    output = os.system(f"'./slicer_data/slicer/{slicer_exec}' '{file}' -g --load {config_file} -o '{temp_gcode}{file_gcode}'")
                    tries += 1
                    
                os.remove(file)
                last_file_change = datetime.now().timestamp()
                if output == 34304:
                    msg('Could not fit object on a buildplate\"', True)
                    return
                if output != 0:
                    msg(f'Some Error Occurred ({output})', True)
                    return
            
                with open(temp_gcode + file_gcode, 'r+') as f:
                    lines = f.readlines()
                    with open(f"{gcodes_dir}{file_gcode}", 'w') as newf:
                        newf.write("; sliced automatically with KlipperSlicer plugin\n")
                        for line in lines:
                            newf.write(line)
                    
                os.remove(temp_gcode + file_gcode)
                msg(f'{file_gcode[:-6]} sliced')
                run_gcode(f"M23 /{file_gcode}")
                run_gcode("M24")
            
            path = os.path.split(file)[0] + '/'
            
            if file[-6:].lower() == '.gcode' and gcodes_dir in path:
                file_wait_for_download(file)
                with open(file, 'r') as f:
                    lines = f.readlines()[:100]
                    for line in lines:
                        if 'sliced automatically' in line:
                            return
                        if 'generated by' in line.lower():
                            set_slicer(line[line.index('by') + 3 : line.index(' on ') ])
                            break

                output = 256
                tries = 0
                while output == 256 and tries < 600:
                    time.sleep(1)
                    output = os.system(f"'./slicer_data/slicer/{slicer_exec}' --load '{file}' --save {config_file}")
                    tries += 1
                msg('Updated Slicer Config')
                last_file_change = datetime.now().timestamp()
                
        except Exception as e:
            msg(str(e.with_traceback()), True)
            
        token = False


event_handler = FileChangeEvent()
observer = Observer()
observer.schedule(event_handler, f"/home/{user}/printer_data/", recursive=True)
observer.start()

while True:
    time.sleep(3600)
