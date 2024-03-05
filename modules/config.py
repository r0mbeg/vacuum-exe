from pydantic import BaseModel, Field, model_validator
from typing import Literal
from .database import Database
import logging


class Config(BaseModel):
    lpu_name: str = Field(description="Name of LPU", alias="lpu-name", default=None)
    iis: Literal[False, True, "true_sendedapi"] = Field(description="Is there an IIS service on the server",
                                                        alias="iis", default=True)
    services: list[str] | None = Field(description="Services list", alias="services", default=[])
    sch_tasks: list[str] | None = Field(description="Scheduler tasks list", alias="sch-tasks", default=[])
    delete_after_days: int = Field(description="(default) Delete old backups after days", alias="delete-after-days",
                                   default=5)
    databases: list[Database] = Field(description="Databases list", alias="databases", default=[])

    @property
    def get_lpu_name(self):
        return self.lpu_name

    @property
    def get_iis(self):
        return self.iis

    @property
    def get_services(self):
        return self.services

    @property
    def get_sch_tasks(self):
        return self.sch_tasks

    @property
    def get_delete_after_days(self):
        return self.delete_after_days

    @property
    def get_databases(self):
        return self.databases

    def set_services(self, services):
        self.services = services

    def set_iis(self, iis):
        self.iis = iis

    @model_validator(mode="after")
    def model_check(self: BaseModel) -> BaseModel:
        """
        LPU name check
        """
        if self.get_lpu_name is None:
            logging.error("LPU name error!")
            raise ValueError("LPU name error!")
        """Delete after days check"""
        if (self.get_delete_after_days is not None and (int(self.get_delete_after_days) != self.get_delete_after_days or
                                                        self.get_delete_after_days < 0 or
                                                        self.get_delete_after_days > 50)):
            logging.error(f"Delete after days {self.get_delete_after_days} error (need 0 < x < 50)!")
            raise ValueError(f"Delete after days {self.get_delete_after_days} error (need 0 < x < 50)!")
        """Databases check"""
        if not self.databases:
            logging.error("Databases list is null!")
            raise ValueError("Databases list is null!")
        return self
