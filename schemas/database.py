import logging
import os.path
import sqlite3
import shutil
import time
import datetime
import re

from pathlib import Path
from py7zr import SevenZipFile
from pydantic import BaseModel, Field, model_validator


def delete_files(path, days, regex):
    current_time = time.time()
    expiration_time = days * 24 * 60 * 60

    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if re.search(regex, file) and (current_time - os.path.getmtime(file_path)) > expiration_time:
                os.remove(file_path)
                logging.info(f"Deleted {file_path}")


def create_7z_archive(input_file: Path, output_archive: Path):
    if Path("7za.exe").exists():
        os.system(f"7za a {output_archive} {input_file}")
    else:
        logging.error(f"7za.exe is missing! 7z archiving is not possible!")




class Database(BaseModel):
    path: Path = Field(description="Path to database", alias="db-path")
    backup_dir: Path = Field(description="Path to backup dir", alias="backup-dir", default=None)
    delete_after_days: int = Field(description="Delete old backups after days", alias="delete-after-days", default=None)

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

    def set_backup_dir(self, x):
        self.backup_dir = x

    def set_delete_after_days(self, x):
        self.delete_after_days = x

    @model_validator(mode="after")
    def model_check(self):
        '''Db path check'''
        if not self.get_path.exists():
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

        return self

    def create_backup(self):
        logging.info(f"Backup of {str(self.get_name)} started")
        logging.info("Deleting old backups and archives")

        delete_files(self.get_backup_dir, self.get_delete_after_days, f"{str(self.get_name)}_backup_.*.db")
        delete_files(self.get_backup_dir, self.get_delete_after_days, f"{str(self.get_name)}_backup_.*.7z")
        delete_files(self.get_backup_dir, self.get_delete_after_days, f"{str(self.get_name)}_archive_.*.db")

        logging.info("Old backups and archives are deleted")

        db_size = os.path.getsize(self.get_path)
        free_space = shutil.disk_usage(self.get_backup_dir).free

        gb = 1073741824

        logging.info(f"Database {str(self.get_name)} weights {db_size} ({round(db_size / gb, 3)} Gb) " +
                     f"(Free space is {free_space} ({round(free_space / gb, 3)} Gb))")

        date_str = datetime.datetime.now().strftime('%d.%m.%Y')

        if db_size * 2.5 < free_space or self.get_name == 'reports':

            backup_filename = f"{self.get_name}_backup_{date_str}"

            logging.info(f"Copy {self.get_name} from {self.get_dir} to {self.get_backup_dir}")
            cmd = f"copy /y {self.get_path} {self.get_backup_dir}\\{self.get_name}_copy_for_backup.db"
            # logging.info(cmd)
            os.system(cmd)
            if Path(f"{self.get_backup_dir}\\{self.get_name}_copy_for_backup.db").exists():
                logging.info(f"Connecting to database {self.get_name}")
                con = sqlite3.connect(f"{self.get_backup_dir}\\{self.get_name}_copy_for_backup.db")
                cur = con.cursor()
                logging.info(f"{self.get_name} backup started")
                cur.execute(f"VACUUM INTO '{self.get_backup_dir}\\{backup_filename}.db';")
                logging.info(f"{self.get_name} backup ended")
                con.commit()
                con.close()

                logging.info(f"Deleting of copy")
                os.remove(f"{self.get_backup_dir}\\{self.get_name}_copy_for_backup.db")

                db_backup_size = os.path.getsize(f"{self.get_backup_dir}\\{backup_filename}.db")
                logging.info(
                    f"Backup {backup_filename}.db weights {db_backup_size} ({round(db_backup_size / gb, 3)} Gb)")
                if db_backup_size / db_size < 0.5:
                    logging.error(f"{self.get_name} backup is too small!")
                else:
                    logging.info(f"{self.get_name} database is backed up SUCCESSFULLY!")
            else:
                logging.error(f"Copy is missing!")
        else:
            logging.error("NOT enough free space for backup!")

    def archive_backup(self):
        date_str = datetime.datetime.now().strftime('%d.%m.%Y')
        backup_filename = f"{self.get_name}_backup_{date_str}"

        if Path(f"{self.get_backup_dir}\\{backup_filename}.db").exists():
            logging.info(f"Archivation of {self.get_name} started")
            create_7z_archive(Path(f"{self.get_backup_dir}\\{backup_filename}.db"),
                              Path(f"{self.get_backup_dir}\\{backup_filename}.7z"))
            if Path(f"{self.get_backup_dir}\\{backup_filename}.7z").exists():
                logging.info(f"Archivation of {self.get_name} ended")
                logging.info(f"Deleting {self.get_backup_dir}\\{backup_filename}.db")
                os.remove(f"{self.get_backup_dir}\\{backup_filename}.db")
        else:
            logging.error(f"Backup of {self.get_name} is missing!")
