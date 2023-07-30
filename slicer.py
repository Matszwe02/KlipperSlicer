import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import os
from datetime import datetime


last_file_change = datetime.now().timestamp()
user = os.listdir('/home')[0]
gcode_console = f"/home/{user}/printer_data/comms/klippy.serial"
slicer_exec = (os.listdir("./slicer_data/slicer/"))[0]
config_file = f"/home/{user}/KlipperSlicer/slicer_data/config.ini"
temp_gcode = f"/home/{user}/KlipperSlicer/slicer_data/gcodes/"
os.system(f"chmod a+x ./slicer_data/slicer/{slicer_exec}")

def run_gcode(command):
    with open(gcode_console, 'a') as console:
        console.write(command + '\n')


def file_wait_for_download(filename):
        file_size = -1
        while file_size != os.path.getsize(filename):
            file_size = os.path.getsize(filename)
            time.sleep(2)


class FileChangeEvent(LoggingEventHandler):        
    def on_created(self, event):
        global last_file_change
        file = event.src_path
        
        if datetime.now().timestamp() - last_file_change < 5: return
        
        if file[-4:].lower() == '.stl':
            if not os.path.exists(config_file):
                run_gcode("RESPOND TYPE=error MSG=\"Slicer: Config.ini missing. Upload any gcode to initialize config file!\"")
                os.remove(file)
                return
            file_gcode = (os.path.basename(file)[:-4] + '.gcode').replace(" ", "_")
            run_gcode("RESPOND PREFIX='Slicer:'  MSG=\"Slicing file...\"")
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
                run_gcode("RESPOND TYPE=error MSG=\"Slicer: Could not fit object on a buildplate\"")
                return
            if output != 0:
                run_gcode(f"RESPOND TYPE=error MSG=\"Slicer: Some Error Occurred ({output})\"")
                return
        
            with open(temp_gcode + file_gcode, 'r+') as f:
                lines = f.readlines()
                with open(f"/home/{user}/printer_data/gcodes/{file_gcode}", 'w') as newf:
                    newf.write("; sliced automatically with KlipperSlicer plugin\n")
                    for line in lines:
                        newf.write(line)
                
            os.remove(temp_gcode + file_gcode)
            run_gcode(f"RESPOND PREFIX='Slicer:'  MSG=\"{file_gcode} sliced\"")
            run_gcode(f"M23 /{file_gcode}")
            run_gcode("M24")
            
        if file[-6:].lower() == '.gcode' and os.path.split(file)[0][-20:] == '/printer_data/gcodes':
            file_wait_for_download(file)
            with open(file, 'r') as f:
                line = f.readlines()[0]
                if 'sliced automatically' in line:
                    return
                
            output = 256
            tries = 0
            while output == 256 and tries < 600:
                time.sleep(1)
                output = os.system(f"'./slicer_data/slicer/{slicer_exec}' --load '{file}' --save {config_file}")
                tries += 1
            run_gcode("RESPOND PREFIX='Slicer:'  MSG=\"Updated Slicer Config\"")
            last_file_change = datetime.now().timestamp()
                
        
event_handler = FileChangeEvent()
observer = Observer()
observer.schedule(event_handler, f"/home/{user}/printer_data/", recursive=True)
observer.start()

while True:
    time.sleep(3600)