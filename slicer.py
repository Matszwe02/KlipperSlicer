import time
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
import os
from datetime import datetime


prevent_file_read = False
last_file_change = datetime.now().timestamp()
user = os.listdir('/home')[0]
gcode_console = f"/home/{user}/printer_data/comms/klippy.serial"
slicer_exec = (os.listdir("./slicer/"))[0]
config_file = f"/home/{user}/Slicer/config.ini"


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
        global prevent_file_read, last_file_change
        file = event.src_path
        
        if prevent_file_read or datetime.now().timestamp() - last_file_change < 5: return
        
        if file[-4:].lower() == '.stl':
            if not os.path.exists(config_file):
                run_gcode("RESPOND TYPE=error MSG=\"Slicer: Config.ini missing. Upload any gcode to initialize config file!\"")
                os.remove(file)
                return
            file_gcode = (os.path.basename(file)[:-4] + '.gcode').replace(" ", "_")
            run_gcode("RESPOND PREFIX='Slicer:'  MSG=\"Slicing file...\"")
            prevent_file_read = True
            output = 256
            tries = 0
            file_wait_for_download(file)
            while output == 256 and tries < 600:
                time.sleep(1)
                output = os.system(f"'./slicer/{slicer_exec}' '{file}' -g --load {config_file} -o '/home/{user}/printer_data/gcodes/{file_gcode}'")
                tries += 1
                
            os.remove(file)
            last_file_change = datetime.now()
            prevent_file_read = False
            if output == 34304:
                run_gcode("RESPOND TYPE=error MSG=\"Slicer: Could not fit object on a buildplate\"")
                return
            if output != 0:
                run_gcode(f"RESPOND TYPE=error MSG=\"Slicer: Some Error Occurred ({output})\"")
                return
                
            run_gcode("RESPOND PREFIX='Slicer:'  MSG=\"File sliced! Printing...\"")
            run_gcode(f"M23 {file_gcode}")
            run_gcode("M24")
        print(os.path.split(file)[0][-20:])
        if file[-6:].lower() == '.gcode' and os.path.split(file)[0][-20:] == '/printer_data/gcodes':
            run_gcode("RESPOND PREFIX='Slicer:'  MSG=\"Updated Slicer Config\"")
            prevent_file_read = True
            output = 256
            tries = 0
            file_wait_for_download(file)
            while output == 256 and tries < 600:
                time.sleep(1)
                output = os.system(f"'./slicer/{slicer_exec}' --load '{file}' --save {config_file}")
                tries += 1
            prevent_file_read = False
            last_file_change = datetime.now()
                
        
event_handler = FileChangeEvent()
observer = Observer()
observer.schedule(event_handler, f"/home/{user}/printer_data/", recursive=True)
observer.start()

while True:
    time.sleep(3600)