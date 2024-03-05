import shutil
import sqlite3
import logging
import os
import re
from modules.os_work import delete_files, get_current_date, get_current_time, archive_backup, load_yaml, move_file
from pathlib import Path
from modules import Config, Database


def create_backup(database: Database):
    logging.info(f"Backup of {str(database.get_name)} started")
    logging.info("Deleting old backups and archives")

    delete_files(database.get_backup_dir, database.get_delete_after_days, fr'^{str(database.get_name)}_backup_.*\.db$')
    delete_files(database.get_backup_dir, database.get_delete_after_days, fr'^{str(database.get_name)}_backup_.*\.7z$')
    if not re.match(fr'^tcgi.*_archive$', str(database.get_name), re.IGNORECASE):
        delete_files(database.get_backup_dir, database.get_delete_after_days, fr'^{str(database.get_name)}_archive_.*\.db$')

    logging.info("Old backups and archives are deleted")

    db_size = os.path.getsize(database.get_path)
    free_space = shutil.disk_usage(database.get_backup_dir).free

    gb = 1073741824

    logging.info(f"Database {str(database.get_name)} weights {db_size} ({round(db_size / gb, 3)} Gb) " +
                 f"(Free space is {free_space} ({round(free_space / gb, 3)} Gb))")

    if db_size * 2.5 < free_space:
        backup_filename = f"{database.get_name}_backup_{get_current_date()}"

        logging.info(f"Copy {database.get_name} from {database.get_dir} to {database.get_backup_dir}")

        if re.match(fr'^tcgi.*_archive$', str(database.get_name), re.IGNORECASE):
            move_file(database.get_path, f'{database.get_backup_dir}\\{database.get_name}_copy_for_backup.db')

        if not Path(f'{database.get_backup_dir}\\{database.get_name}_copy_for_backup.db').exists():
            shutil.copy(database.get_path, f'{database.get_backup_dir}\\{database.get_name}_copy_for_backup.db')

        if Path(f"{database.get_backup_dir}\\{database.get_name}_copy_for_backup.db").exists():
            logging.info(f"Connecting to database {database.get_name}")
            con = sqlite3.connect(f"{database.get_backup_dir}\\{database.get_name}_copy_for_backup.db")
            cur = con.cursor()
            logging.info(f"{database.get_name} backup started")
            if Path(f'{database.get_backup_dir}\\{backup_filename}.db').exists():
                os.rename(f'{database.get_backup_dir}\\{backup_filename}.db',
                          f'{database.get_backup_dir}\\{backup_filename}_copy_' + f'{get_current_time()}'.replace(':',
                                                                                                                  '_') + '.db')
            cur.execute(f"VACUUM INTO '{database.get_backup_dir}\\{backup_filename}.db';")

            logging.info(f"{database.get_name} backup ended")
            con.commit()
            con.close()

            logging.info(f"Deleting of {database.get_name}_copy_for_backup")

            os.remove(f"{database.get_backup_dir}\\{database.get_name}_copy_for_backup.db")

            db_backup_size = os.path.getsize(f"{database.get_backup_dir}\\{backup_filename}.db")
            logging.info(f"Backup {backup_filename}.db weights {db_backup_size} ({round(db_backup_size / gb, 3)} Gb)")
            if db_backup_size / db_size < 0.5:
                logging.error(f"{database.get_name} backup is too small!")
            else:
                logging.info(f"{database.get_name} database is backed up SUCCESSFULLY!")
        else:
            logging.error(f"Copy is missing!")

    else:
        logging.error("NOT enough free space for backup!")


if __name__ == "__main__":
    log_file = f"backup_{get_current_date()}.log"

    logging.basicConfig(level=logging.INFO, filename=log_file, filemode='a',
                        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
                        datefmt='%d.%m.%Y %H:%M:%S')

    with open(log_file, 'a') as f:
        f.write(f"\n")
    logging.info("NEW BACKUP STARTED")

    config_yaml = load_yaml(Path("config.yml"))
    config = Config.model_validate(config_yaml)

    logging.info("Deleting old logs")
    delete_files(Path.cwd(), config.get_delete_after_days, fr"^backup_.*.log$")
    logging.info("Old logs deleted")



    # deleting dublicates and bad db's from list
    config.databases = [db for db in config.databases if db is not None]

    for db in config.databases:
        if db.get_delete_after_days is None:
            db.set_delete_after_days(config.get_delete_after_days)

    for db in config.databases:
        create_backup(db)

    for db in config.databases:
        archive_backup(db)
