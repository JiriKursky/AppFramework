import yaml
from helper_tools import MyHelp as h
from helper_types import DictType, StrType


class Private(object):
    def __init__(self):
        secrets_file = h.config_path() + "secrets.yaml"
        self.config: DictType = self._get_config(secrets_file)

        if self.config is None:
            secrets_file = "/conf/secrets.yaml"
            # For case of debugging in docker
            self.config = self._get_config(secrets_file)

        self.error = self.config is None

    def _get_config(self, filename: str) -> DictType:
        """Reading directly file

        Args:
            filename (str): yaml

        Returns:
            dict: all secrets
        """
        if h.file_exists(filename):
            with open(filename, "r") as stream:
                retval = yaml.safe_load(stream)
            return retval
        else:
            return None

    def get_secret(self, key: str) -> StrType:
        """Returns secret key

        Args:
            key (str): key from secret

        Returns:
            StrType: str|None
        """
        if self.error:
            return None
        else:
            return h.par(self.config, key)
