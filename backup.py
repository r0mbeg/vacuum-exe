import yaml
import logging
import typing as tp
import os
from schemas import Config
from pathlib import Path
import time
import datetime
import re


def delete_files(path, days, regex):
    current_time = time.time()
    expiration_time = days * 24 * 60 * 60

    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            if re.search(regex, file) and (current_time - os.path.getmtime(file_path)) > expiration_time:
                os.remove(file_path)
                logging.info(f"Deleted {file_path}")


def start_services(services, sch_tasks, iis):
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


def stop_services(services, sch_tasks, iis):
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


date_str = datetime.datetime.now().strftime('%d.%m.%Y')
log_file = f"backup_{date_str}.log"

logging.basicConfig(level=logging.INFO, filename=log_file, filemode='a',
                    format="%(asctime)s %(levelname)s: %(message)s")
with open(log_file, 'a') as f:
    f.write("\nNEW BACKUP STARTED \n")

if __name__ == "__main__":

    config_yaml = load_yaml(Path("config.yml"))
    config = Config.model_validate(config_yaml)

    logging.info("Deleting old logs")
    delete_files(Path.cwd(), config.get_delete_after_days, fr"^backup_.*.log$")
    logging.info("Old logs deleted")

    for db in config.databases:
        if db is None:
            config.databases.remove(db)
        else:
            if db.get_delete_after_days is None:
                db.set_delete_after_days(config.get_delete_after_days)

    for db in config.databases:
        db.create_backup()
    for db in config.databases:
        db.archive_backup()
