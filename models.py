import datetime
from tortoise.models import Model
from tortoise import fields
from pydantic import BaseModel


class GeigerCounter(Model):
    """
    A geiger counter.
    """

    id = fields.IntField(pk=True)
    geigerc_id = fields.CharField(max_length=255)
    owner_id = fields.CharField(max_length=255)

    class Meta:
        unique_together = (("geigerc_id", "owner_id"),)

    def __str__(self):
        return f"{self.owner_id}-{self.counter_id}"


class Measurement(Model):
    """
    One measurement made by a geiger counter
    """

    id = fields.IntField(pk=True)
    counter = fields.ForeignKeyField(
        "models.GeigerCounter", related_name="measurements"
    )
    cpm = fields.IntField(description="counts per minute")
    acpm = fields.IntField(description="Average counts per minute")
    usv = fields.FloatField(description="Value in micro sieverts")
    time = fields.DatetimeField(
        auto_now_add=True, description="Date of the measurement"
    )


class ApiMeasurement(BaseModel):
    """
    pydantic model for measurement
    """

    class Config:
        orm_mode = True

    cpm: int
    acpm: int
    usv: float
    time: datetime.datetime
