import datetime

import yaml

run_info = {
    'night_start': datetime.datetime.utcnow().isoformat(),
    'num_night_runs': 0,
    'chiller_on': False,
    'fans_on': False,
    'shutter_open': False,
    'target_name': "NONE",
    'ra': None,
    'dec': None,
    'flasher_on': False,
    'flasher_rate': 0,
    'top_flasher_LED': "0000000000",
    'middle_flasher_LED': "0000000000",
    'bottom_flasher_LED': "0000000000"
    }

with open('.run_info.yml', 'w') as run_info_file:
    yaml.dump(run_info, run_info_file, default_flow_style=False)
