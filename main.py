import os
import subprocess
import time
import shutil
import configparser
import re
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from PythonMoonraker.api import MoonrakerAPI
from PythonMoonraker.websocket import MoonrakerWS
import GcodeTools


moonraker_url = 'localhost'

api = MoonrakerAPI(moonraker_url)
ws = MoonrakerWS(moonraker_url)


allowed_extensions = ['stl', '3mf', 'obj', 'step', 'stp', 'amf']


class Config:
    def __init__(self):
        self.slicer_name = None
        self.slicer_executable = None
        self.slicer_args = None
        self.slicer_workdir = None
        self.system_workdir = None
        self.lookup_paths = None
        self.skip_files = None
        self.auto_update_config = None
        self.remove_original_files = None
        self.auto_start_print = None
        self.gcode_when_slicing = None

    def _read_config(self):
        files = api.server_files_list('config')['result']
        for file in files:
            if file['path'] == 'klipper_slicer.conf':
                return api.server_files('config', 'klipper_slicer.conf').decode()
        with open('klipper_slicer.conf') as f:
            body = f.read()
            api.server_files_upload('klipper_slicer.conf', body, 'config')
            return body

    def load_config(self):
        cfg = configparser.ConfigParser()
        cfg.read_string(self._read_config())
        print(cfg.sections())
        print(cfg['slicer'].get('args').split())
        for section in cfg.sections():
            for setting in cfg[section].keys():
                value = cfg[section][setting].strip()
                print(f'{setting=}, {value=}, {type(value)=}')
                if setting == 'name': self.slicer_name = value
                if setting == 'executable': self.slicer_executable = value
                if setting == 'args': self.slicer_args = value.split()
                if setting == 'workdir': self.slicer_workdir = value
                if setting == 'system_workdir': self.system_workdir = value
                if setting == 'lookup_paths': self.lookup_paths = value.split()
                if setting == 'skip_files': self.skip_files = value
                if setting == 'auto_update_config': self.auto_update_config = bool(value)
                if setting == 'auto_start_print': self.auto_start_print = bool(value)
                if setting == 'remove_original_files': self.remove_original_files = bool(value)
                if setting == 'gcode_when_slicing': self.gcode_when_slicing = value.splitlines()

        if self.system_workdir is None: self.system_workdir = self.slicer_workdir
        os.makedirs(self.system_workdir, exist_ok=True)



def update_config_from_gcode(gcode_str: str):
    if not config.auto_update_config: return
    if '; Sliced using KlipperSlicer' in gcode_str[:50]:
        print('File sliced with KlipperSlicer - skipping')
        return
    g = GcodeTools.Gcode(gcode_str=gcode_str)
    slicer = GcodeTools.Tools.get_slicer_name(g)[0]
    if slicer.lower() != config.slicer_name:
        print('Received gcode from different slicer - skipping')
        return
    print('updating config file from gcode')
    files = GcodeTools.Tools.generate_config_files(g)
    for key in files.keys():
        with open(os.path.join(config.system_workdir, key), 'w') as f:
            f.write(files[key])
    return



config = Config()
config.load_config()

created_file = None
observers = {}


class FileChangeEvent(LoggingEventHandler):        
    def on_created(self, event):
        if event.src_path.endswith('.gcode'):
            with open(event.src_path, 'r') as f:
                update_config_from_gcode(f.read())
        elif event.src_path.split('.')[-1] in allowed_extensions:
            if re.match(config.skip_files, os.path.basename(event.src_path)):
                print('Skipping excluded file')
                return
            global created_file
            created_file = event.src_path


event_handler = FileChangeEvent()

for path in config.lookup_paths:
    if not path.startswith('/'): continue
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    observers[path] = observer


def handle_message(data: dict):
    if data.get('params', [{}])[0].get('action', '') == 'create_file':
        print(data)
        item = data['params'][0]['item']
        if item['root'] == 'gcodes' and item['path'].endswith('.gcode'):
            gcode_str=api.server_files(item['root'], item['path']).decode()
            update_config_from_gcode(gcode_str)
            return
        for path in config.lookup_paths:
            if path.startswith(item['root']): break
        else:
            return
        if item['path'].split('.')[-1] in allowed_extensions:
            if re.match(config.skip_files, os.path.basename(item['path'])):
                print('Skipping excluded file')
                return
            global created_file
            created_file = [item['root'], item['path']]



def get_file_to_slice():
    if created_file:
        if type(created_file) == str:
            final_path = os.path.join(config.system_workdir, os.path.basename(created_file))
            shutil.copy(created_file, final_path)
        else:
            final_path = os.path.join(config.system_workdir, created_file[1])
            with open(final_path, 'wb') as f:
                f.write(api.server_files(created_file[0], created_file[1]))
        return os.path.basename(final_path)



def remove_file():
    if created_file:
        if type(created_file) == str:
            os.remove(created_file)
        else:
            api.server_files_delete(created_file[0], created_file[1])



def slice_file(filename: str):
    cmd = [config.slicer_executable]
    if config.slicer_name.lower() in ['orcaslicer']:
        workdir = config.slicer_workdir
        machine = os.path.join(workdir, "machine.json")
        process = os.path.join(workdir, "process.json")
        filament = os.path.join(workdir, "filament.json")
        cmd.extend(['--load-settings', f'{machine};{process}', '--load-filaments', f'{filament}'])
        cmd.extend(['--slice', '0', '--allow-newer-file'])
        cmd.extend(['--outputdir', workdir])
        cmd.extend(['--datadir', workdir])
        cmd.extend(['--export-slicedata', workdir])
        # TODO: support other slicers - port legacy logic
    cmd.append(os.path.join(workdir, filename))
    cmd.extend(config.slicer_args)
    print(f'calling "{cmd}"')
    subprocess.call(cmd)

    print('File sliced successfully!')
    
    new_filename = filename.removesuffix(filename.split('.')[-1]) + 'gcode'
    for file in os.listdir(config.system_workdir):
        if file.endswith('.gcode'):
            shutil.move(os.path.join(config.system_workdir, file), os.path.join(config.system_workdir, new_filename))
    with open(os.path.join(config.system_workdir, new_filename), 'r+') as f:
        content = f.read()
        f.seek(0, 0)
        f.write('; Sliced using KlipperSlicer' + '\n' + content)
    return new_filename



def upload_gcode(path: str):
    filename = os.path.basename(path)
    with open(path, 'rb') as f:
        file = f.read()
    api.server_files_upload(filename, file)



def main():
    global created_file
    ws.start_websocket_loop(handle_message)
    try:
        while True:
            filename = get_file_to_slice()
            if filename:
                if config.gcode_when_slicing:
                    api.api_printer_command(config.gcode_when_slicing)
                gcode_filename = slice_file(filename)
                upload_gcode(os.path.join(config.system_workdir, gcode_filename))
                if config.auto_start_print:
                    api.api_printer_command([f'M23 {gcode_filename}', 'M24'])
                if config.remove_original_files:
                    remove_file()
                created_file = None
                os.remove(os.path.join(config.system_workdir, gcode_filename))
                os.remove(os.path.join(config.system_workdir, filename))


            time.sleep(10)
    except KeyboardInterrupt:
        ws.stop_websocket_loop()

if __name__ == '__main__':
    main()
