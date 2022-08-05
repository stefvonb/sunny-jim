from dashboard.dashboard import Dashboard
from configuration import config


if __name__ == "__main__":
    dashboard = Dashboard(config)
    dashboard.run()
