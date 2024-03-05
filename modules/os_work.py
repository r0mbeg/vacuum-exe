import shutil

import yaml
import logging
import typing as tp
import os
from pathlib import Path
import time
import datetime
import re
from modules import Config, Database


def get_current_time():
    return datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]


def get_current_date():
    return datetime.datetime.now().strftime('%d.%m.%Y')


def create_7z_archive(input_file: Path, output_archive: Path):
    if Path("7za.exe").exists():
        os.system(f"7za a {output_archive} {input_file}")
    else:
        logging.error(f"7za.exe is missing! 7z archiving is not possible!")


def delete_files(path: Path, days: int, regex: str):
    current_time = time.time()
    expiration_time = days * 24 * 60 * 60

    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if re.search(regex, file) and (current_time - os.path.getmtime(file_path)) > expiration_time:
                os.remove(file_path)
                logging.info(f"Deleted {file_path}")


def move_file(source, destination, max_tries=5):
    for _ in range(max_tries):
        try:
            shutil.move(source, destination)
            return
        except Exception as e:
            print(f"File transfer error. Attempt {_ + 1}/{max_tries}. Error: {e}")
            time.sleep(5)


def start_services(services: [str], sch_tasks: [str], iis: str):
    for serv in services:
        logging.info("Turning on \"" + serv + "\" service")
        logging.info("sc start \"" + serv + "\"")
        os.system("sc start \"" + serv + "\"")

    for task in sch_tasks:
        logging.info("Turning on \"" + task + "\" task")
        logging.info("schtasks /change /tn \" " + task + "\" /enable")
        os.system("schtasks /change /tn \" " + task + "\" /enable")

    if iis:
        logging.info("Turning on IIS service")
        logging.info("iisreset /start")
        os.system("iisreset /start")


def stop_services(services: [str], sch_tasks: [str], iis: str):
    logging.info("Stopping SQLiteStudio")
    logging.info("Taskkill /IM SQLiteStudio.exe /F")
    os.system("Taskkill /IM SQLiteStudio.exe /F")

    for serv in services:
        logging.info("Turning off \"" + serv + "\" service")
        logging.info("sc stop \"" + serv + "\"")
        os.system("sc stop \"" + serv + "\"")

    for task in sch_tasks:
        logging.info("Turning off \"" + task + "\" task")
        logging.info("schtasks /end /tn \"" + task + "\"")
        logging.info("schtasks /change /tn \" " + task + "\" /disable")
        os.system("schtasks /end /tn \"" + task + "\"")
        os.system("schtasks /change /tn \" " + task + "\" /disable")

    if iis:
        logging.info("Turning off IIS service")
        logging.info("iisreset /stop")
        os.system("iisreset /stop")


def load_yaml(path: Path) -> dict[str, tp.Any]:
    if path.exists():
        logging.info("Config file reading started")
        with Path(path).open("r") as f:
            cfg_yaml = yaml.safe_load(f)
        if not isinstance(cfg_yaml, dict):
            logging.error(f"Config file has no top-level mapping: {path}")

            raise TypeError(f"Config file has no top-level mapping: {path}")
        return cfg_yaml
    else:
        logging.error("Config file does not exist!")
        exit()


def archive_backup(database: Database):
    backup_filename = f"{database.get_name}_backup_{get_current_date()}"

    if Path(f"{database.get_backup_dir}\\{backup_filename}.db").exists():
        logging.info(f"Archivation of {database.get_name} started")
        create_7z_archive(Path(f"{database.get_backup_dir}\\{backup_filename}.db"),
                          Path(f"{database.get_backup_dir}\\{backup_filename}.7z"))
        if Path(f"{database.get_backup_dir}\\{backup_filename}.7z").exists():
            logging.info(f"Archivation of {database.get_name} ended")
            logging.info(f"Deleting {database.get_backup_dir}\\{backup_filename}.db")
            os.remove(f"{database.get_backup_dir}\\{backup_filename}.db")
    else:
        logging.error(f"Backup of {database.get_name} is missing!")
