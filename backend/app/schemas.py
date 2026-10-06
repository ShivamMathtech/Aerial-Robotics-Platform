from typing import Literal
from pydantic import BaseModel as PydanticBaseModel, Field, ConfigDict

class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

class Vector(BaseModel):
    x: float = Field(allow_inf_nan=False)
    y: float = Field(allow_inf_nan=False)
    z: float = Field(allow_inf_nan=False)
class Orientation(BaseModel):
    roll: float
    pitch: float
    yaw: float
class Position(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    alt: float = Field(ge=0)
    x: float
    y: float
class Battery(BaseModel):
    percentage: float = Field(ge=0, le=100)
    voltage: float
    current: float
class GPS(BaseModel):
    satellites: int = Field(ge=0)
    fix: Literal['NO FIX','2D','3D']
    hdop: float
class Telemetry(BaseModel):
    type: Literal['telemetry'] = 'telemetry'
    vehicle_id: str = 'DR-001'
    timestamp: str
    sim_time: float
    sequence: int
    position: Position
    velocity: Vector
    acceleration: Vector
    gyro: Vector
    orientation: Orientation
    battery: Battery
    gps: GPS
    rssi: float
    temperature: float
    throttle: float
    rate: int
    packet_loss: float
    packets_lost: int
    latency: float
    state: str
    mode: str
    armed: bool
    health: str
    scenario: str
    paused: bool
    detections: list[dict]

Scenario = Literal['HOVER','TAKEOFF','CLIMB','CRUISE','ORBIT','TURN','DESCENT','LANDING','GPS FAILURE','LOW BATTERY','COMMUNICATION FAILURE','SENSOR ANOMALY']
class CommandIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['ARM','DISARM','EMERGENCY_STOP','RESET','PAUSE','RESUME','LAND','RTH','SET_MODE','SET_CONTROL','SET_SCENARIO']
    value: str | float | dict[str,float] | None = None
    source: str = Field(default='dashboard',max_length=80)
class MissionIn(BaseModel):
    name: str = Field(min_length=1,max_length=120)
    description: str = Field(default='',max_length=2000)
    target_altitude: float = Field(default=150,ge=0,le=500)
    max_speed: float = Field(default=20,gt=0,le=50)
class MissionStatus(BaseModel):
    status: Literal['PLANNED','RUNNING','PAUSED','COMPLETED','ABORTED']
class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    rate: int = Field(default=50,ge=5,le=50)
    speed: float = Field(default=1,ge=.25,le=10)
    seed: int = Field(default=42,ge=0,le=2147483647)
    battery_warning: float = Field(default=30,ge=16,le=90)
    rssi_warning: float = Field(default=-85,ge=-110,le=-40)
    gps_warning: int = Field(default=6,ge=3,le=12)
class WaypointIn(BaseModel):
    lat: float = Field(ge=-90,le=90)
    lon: float = Field(ge=-180,le=180)
    altitude: float = Field(default=150,ge=0,le=500)
