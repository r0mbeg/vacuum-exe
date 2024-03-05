import logging

from typing import Literal
from pathlib import Path
from pydantic import BaseModel, Field, model_validator


class Database(BaseModel):
    path: Path = Field(description="Path to database", alias="db-path")
    backup_dir: Path = Field(description="Path to backup dir", alias="backup-dir", default=None)
    delete_after_days: int = Field(description="Delete old backups after days", alias="delete-after-days", default=None)
    enable_vacuum: Literal[False, True] = Field(description="Enable vacuum for this base",
                                                alias="enable-vacuum", default=True)

    @property
    def get_path(self):
        return self.path

    @property
    def get_name(self):
        return Path(str(self.get_path.stem))

    @property
    def get_dir(self):
        return Path(str(self.path)[0:str(self.path).index(str(self.path.name))])

    @property
    def get_backup_dir(self):
        if self.backup_dir is None:
            return Path(str(self.path)[0:str(self.path).index(str(self.path.name))])
        else:
            return self.backup_dir

    @property
    def get_delete_after_days(self):
        return self.delete_after_days

    @property
    def get_enable_vacuum(self):
        return self.enable_vacuum

    def set_backup_dir(self, x):
        self.backup_dir = x

    def set_delete_after_days(self, x):
        self.delete_after_days = x

    def set_enable_vacuum(self, x):
        self.enable_vacuum = x

    @model_validator(mode="after")
    def model_check(self):
        '''Db path check'''
        if not self.get_path.exists() or not self.get_path.is_file():
            logging.error(f"Database path {self.get_path} does not exist!")
            return None
            # raise ValueError(f"Database path {self.get_path} doesn't exist!")

        '''Backup dir check'''
        if (not self.get_backup_dir.exists() or
                not self.get_backup_dir.is_dir() or
                self.get_backup_dir is None):
            logging.error(f"Backup path {self.get_backup_dir} does not exist! Using DEFAULT instead")
            self.set_backup_dir(None)
        self.set_backup_dir(self.get_backup_dir)

        # raise ValueError(f"Backup path {self.get_backup_dir} doesn't exist!")

        '''Special delete after days check'''
        if (self.get_delete_after_days is not None and (int(self.get_delete_after_days) != self.get_delete_after_days or
                                                        self.get_delete_after_days < 0 or
                                                        self.get_delete_after_days > 50)):
            logging.error(f"Special delete after days {self.get_delete_after_days} error (need 0 < x < 50)!")
            self.set_delete_after_days(None)
            # raise ValueError(f"Special delete after days {self.get_delete_after_days} error (need 0 < x < 50)!")

        '''Enable vacuum check'''
        if self.get_enable_vacuum not in [True, False]:
            logging.error(f"Enable vacuum setting error!")
            self.set_enable_vacuum(True)

        return self
