import yaml


class Config:
    def __init__(self, config_filename: str):
        with open(config_filename, 'r') as config_file:
            self.config_dictionary = yaml.load(config_file)
            