from dashboard.dashboard import Dashboard
import yaml

# Open up a config file
with open("config.yaml", 'r') as config_file:
    config = yaml.safe_load(config_file)

if __name__ == "__main__":
    dashboard = Dashboard(config)
    dashboard.run()
