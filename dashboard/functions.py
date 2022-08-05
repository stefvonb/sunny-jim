from glob import glob
import yaml


def update_logs_data(n_intervals):
    with open("config.yaml", 'r') as config_file:
        config = yaml.safe_load(config_file)
    log_files = sorted(glob(config["application"]["logs"]["log_filename"] + "*"))
    most_recent_log_file = log_files[-1]

    javascript_to_run = '''
                 var textarea = document.getElementById('logs-textarea');
                 textarea.scrollTop = textarea.scrollHeight;
                 '''

    with open(most_recent_log_file, "r") as f:
        lines = f.readlines()[-1000:]
        return "".join(lines), javascript_to_run
