import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Float, Integer, Boolean, ForeignKey, JSON, Text, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, relationship

def now(): return datetime.now(timezone.utc).isoformat()
class Base(DeclarativeBase): pass
class Vehicle(Base):
    __tablename__='vehicles'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    name: Mapped[str]=mapped_column(String)
    adapter: Mapped[str]=mapped_column(String,default='simulator')
    missions: Mapped[list['Mission']]=relationship(back_populates='vehicle')
class Mission(Base):
    __tablename__='missions'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    vehicle_id: Mapped[str]=mapped_column(ForeignKey('vehicles.id'))
    name: Mapped[str]=mapped_column(String)
    description: Mapped[str]=mapped_column(Text,default='')
    status: Mapped[str]=mapped_column(String,default='PLANNED')
    start_time: Mapped[str]=mapped_column(String,default=now)
    target_altitude: Mapped[float]=mapped_column(Float,default=150)
    max_speed: Mapped[float]=mapped_column(Float,default=20)
    vehicle: Mapped[Vehicle]=relationship(back_populates='missions')
    sessions: Mapped[list['TelemetrySession']]=relationship(back_populates='mission')
    waypoints: Mapped[list['Waypoint']]=relationship(back_populates='mission')
class TelemetrySession(Base):
    __tablename__='telemetry_sessions'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    vehicle_id: Mapped[str]=mapped_column(ForeignKey('vehicles.id'))
    mission_id: Mapped[str | None]=mapped_column(ForeignKey('missions.id'),nullable=True)
    start_time: Mapped[str]=mapped_column(String,default=now)
    end_time: Mapped[str | None]=mapped_column(String,nullable=True)
    status: Mapped[str]=mapped_column(String,default='RECORDING')
    mission: Mapped[Mission | None]=relationship(back_populates='sessions')
    points: Mapped[list['TelemetryPoint']]=relationship(back_populates='session',cascade='all, delete-orphan')
class TelemetryPoint(Base):
    __tablename__='telemetry_points'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    session_id: Mapped[str]=mapped_column(ForeignKey('telemetry_sessions.id'),index=True)
    sim_time: Mapped[float]=mapped_column(Float)
    data: Mapped[dict]=mapped_column(JSON)
    session: Mapped[TelemetrySession]=relationship(back_populates='points')
class Command(Base):
    __tablename__='commands'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    session_id: Mapped[str | None]=mapped_column(ForeignKey('telemetry_sessions.id'),nullable=True,index=True)
    timestamp: Mapped[str]=mapped_column(String,default=now)
    type: Mapped[str]=mapped_column(String)
    source: Mapped[str]=mapped_column(String)
    status: Mapped[str]=mapped_column(String)
    error: Mapped[str | None]=mapped_column(String,nullable=True)
    value: Mapped[object | None]=mapped_column(JSON,nullable=True)
class Alert(Base):
    __tablename__='alerts'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    rule: Mapped[str]=mapped_column(String)
    severity: Mapped[str]=mapped_column(String)
    timestamp: Mapped[str]=mapped_column(String,default=now)
    message: Mapped[str]=mapped_column(String)
    acknowledged: Mapped[bool]=mapped_column(Boolean,default=False)
    active: Mapped[bool]=mapped_column(Boolean,default=True)
class Event(Base):
    __tablename__='events'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    session_id: Mapped[str | None]=mapped_column(ForeignKey('telemetry_sessions.id'),nullable=True,index=True)
    mission_id: Mapped[str | None]=mapped_column(ForeignKey('missions.id'),nullable=True)
    timestamp: Mapped[str]=mapped_column(String,default=now)
    kind: Mapped[str]=mapped_column(String)
    message: Mapped[str]=mapped_column(String)
class Camera(Base):
    __tablename__='cameras'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    vehicle_id: Mapped[str]=mapped_column(ForeignKey('vehicles.id'))
    name: Mapped[str]=mapped_column(String)
    adapter: Mapped[str]=mapped_column(String,default='simulated')
class Detection(Base):
    __tablename__='detections'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    session_id: Mapped[str]=mapped_column(ForeignKey('telemetry_sessions.id'),index=True)
    camera_id: Mapped[str]=mapped_column(ForeignKey('cameras.id'))
    data: Mapped[dict]=mapped_column(JSON)
class Waypoint(Base):
    __tablename__='waypoints'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    mission_id: Mapped[str]=mapped_column(ForeignKey('missions.id'))
    lat: Mapped[float]=mapped_column(Float)
    lon: Mapped[float]=mapped_column(Float)
    altitude: Mapped[float]=mapped_column(Float)
    mission: Mapped[Mission]=relationship(back_populates='waypoints')
class SystemConfiguration(Base):
    __tablename__='system_configuration'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    data: Mapped[dict]=mapped_column(JSON)
class User(Base):
    """Reserved identity model; local API key auth is implemented, user login is not."""
    __tablename__='users'
    id: Mapped[str]=mapped_column(String,primary_key=True)
    name: Mapped[str]=mapped_column(String)
    role: Mapped[str]=mapped_column(String,default='observer')

def database(url=None):
    url=url or os.getenv('DATABASE_URL','sqlite:///./aerial.db')
    engine=create_engine(url,connect_args={'check_same_thread':False} if url.startswith('sqlite') else {},pool_pre_ping=True)
    if url.startswith('sqlite'):
        @event.listens_for(engine,'connect')
        def pragmas(conn, _):
            conn.execute('PRAGMA foreign_keys=ON'); conn.execute('PRAGMA journal_mode=WAL')
    Base.metadata.create_all(engine)
    return engine, sessionmaker(engine,expire_on_commit=False)

def serialize(row):
    return {column.name:getattr(row,column.name) for column in row.__table__.columns}
