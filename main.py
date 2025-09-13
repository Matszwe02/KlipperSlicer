import configparser
from PythonMoonraker.api import MoonrakerAPI
from PythonMoonraker.websocket import MoonrakerWS


moonraker_url = 'localhost'

api = MoonrakerAPI(moonraker_url)
ws_client = MoonrakerWS(moonraker_url)


def load_config():
    files = api.server_files_list('config')['result']
    for file in files:
        if file['path'] == 'klipper_slicer.conf':
            return api.server_files('config', 'klipper_slicer.conf').decode()
    with open('klipper_slicer.conf') as f:
        body = f.read()
        api.server_files_upload('klipper_slicer.conf', body, 'config')
        return body



cfg = configparser.ConfigParser()
cfg.read_string(load_config())
print(cfg.sections())
print(cfg['slicer'].get('args').split())


def handle_message(data: dict):
    if data.get('params', [{}])[0].get('action', '') == 'create_file':
        print(data['params'])
        print(data['params'][0]['item']['path'])
        print(data['params'][0]['item']['root'])


def main():
    ws_client.start_websocket_loop(handle_message)
    try:
        while True:
            pass
    except KeyboardInterrupt:
        ws_client.stop_websocket_loop()

if __name__ == '__main__':
    main()
