import os
import time
import shutil
import configparser
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from PythonMoonraker.api import MoonrakerAPI
from PythonMoonraker.websocket import MoonrakerWS


moonraker_url = 'localhost'

api = MoonrakerAPI(moonraker_url)
ws = MoonrakerWS(moonraker_url)





class Config:
    def __init__(self):
        self.slicer_executable = None
        self.slicer_args = None
        self.slicer_workdir = None
        self.lookup_paths = None
        self.skip_files = None
        self.auto_update_config = None

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
                value = cfg[section][setting]
                print(f'{setting=}, {value=}, {type(value)=}')
                if setting == 'executable': self.slicer_executable = value
                if setting == 'args': self.slicer_args = value.split()
                if setting == 'workdir': self.slicer_workdir = value
                if setting == 'lookup_paths': self.lookup_paths = value.split()
                if setting == 'skip_files': self.skip_files = value
                if setting == 'auto_update_config': self.auto_update_config = bool(value)


config = Config()
config.load_config()

created_file = None
observers = {}


class FileChangeEvent(LoggingEventHandler):        
    def on_created(self, event):
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
        item = data['params'][0]['item']
        for path in config.lookup_paths:
            if path.startswith(item['root']): break
        else:
            return
        global created_file
        created_file = [item['root'], item['path']]



def get_file_to_slice():
    global created_file
    if created_file:
        if type(created_file) == str:
            final_path = os.path.join(config['workdir'], os.path.basename(created_file))
            shutil.move(created_file, final_path)
        else:
            final_path = os.path.join(config['workdir'], created_file[1])
            with open(final_path, 'wb') as f:
                f.write(api.server_files(created_file[0], created_file[1]))
        created_file = None
        return final_path


def main():
    ws.start_websocket_loop(handle_message)
    try:
        while True:
            filename = get_file_to_slice()
            print(filename)
    except KeyboardInterrupt:
        ws.stop_websocket_loop()

if __name__ == '__main__':
    main()
