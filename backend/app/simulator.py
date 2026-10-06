"""Deterministic fixed-step, physics-inspired software vehicle. ENU coordinates."""
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Protocol
from .schemas import Telemetry, Settings

HOME = (30.3165, 78.0322)
SCENARIOS = ['HOVER','TAKEOFF','CLIMB','CRUISE','ORBIT','TURN','DESCENT','LANDING','GPS FAILURE','LOW BATTERY','COMMUNICATION FAILURE','SENSOR ANOMALY']
MODES = ['MANUAL','STABILIZE','ALTITUDE HOLD','POSITION HOLD','AUTO']

class VehicleAdapter(Protocol):
    def connect(self) -> None: ...
    def disconnect(self) -> None: ...
    def send_command(self, kind: str, value=None) -> None: ...
    def get_telemetry(self) -> Telemetry: ...
    def get_status(self) -> dict: ...

class HardwareAdapter:
    """Extension contract only. No transport or real-world command implementation."""
    def connect(self): raise NotImplementedError('Hardware adapter is not implemented')
    def disconnect(self): pass
    def send_command(self, kind, value=None): raise NotImplementedError('Simulation only')
    def get_telemetry(self): raise NotImplementedError
    def get_status(self): return {'connected':False,'implemented':False}

class SimulatorAdapter:
    def __init__(self, settings=None):
        self.settings = settings or Settings()
        self.reset()
    def reset(self):
        self.rng = random.Random(self.settings.seed)
        self.epoch = datetime(2026,1,1,tzinfo=timezone.utc)
        self.time=0.; self.seq=0; self.x=0.; self.y=0.; self.alt=124.6
        self.vx=0.; self.vy=0.; self.vz=0.; self.roll=0.; self.pitch=0.; self.yaw=87.4
        self.battery=78.; self.temp=32.; self.rssi=-62.; self.loss=0.; self.lost=0
        self.gps_elapsed=0.; self.satellites=14; self.throttle=50.; self.controls={'yaw':0.,'pitch':0.,'roll':0.}
        self.mode='MANUAL'; self.armed=True; self.state='FLIGHT'; self.scenario='CRUISE'
        self.paused=False; self.connected=True; self.returning=False
        self.acc=(0.,0.,9.81); self.gyro=(0.,0.,0.)
    def connect(self): self.connected=True
    def disconnect(self): self.connected=False
    def get_status(self): return {'connected':self.connected,'simulation':True,'paused':self.paused,'state':self.state}
    def send_command(self, kind, value=None):
        if kind=='RESET': self.reset(); return
        if kind=='EMERGENCY_STOP':
            self.armed=False; self.state='EMERGENCY'; self.vx=self.vy=self.vz=0; self.throttle=0; return
        if kind=='ARM': self.armed=True; self.state='ARMED'
        elif kind=='DISARM': self.armed=False; self.state='DISARMED'; self.throttle=0
        elif kind=='PAUSE': self.paused=True
        elif kind=='RESUME': self.paused=False
        elif kind=='LAND': self.scenario='LANDING'; self.returning=False
        elif kind=='RTH': self.returning=True; self.scenario='HOVER'
        elif kind=='SET_MODE': self.mode=value
        elif kind=='SET_CONTROL':
            for key,val in value.items():
                if key=='throttle': self.throttle=val
                else: self.controls[key]=val
        elif kind=='SET_SCENARIO':
            self.scenario=value; self.returning=False
            if value=='TAKEOFF': self.alt=0; self.vz=0; self.armed=True; self.state='TAKEOFF'
    def step(self, dt):
        if self.paused or not self.connected: return self.get_telemetry()
        self.time+=dt; self.seq+=1
        t=self.time; s=self.scenario
        old=(self.vx,self.vy,self.vz); angles=(self.roll,self.pitch,self.yaw)
        if self.armed and self.state!='EMERGENCY':
            self.state='LANDING' if s=='LANDING' else ('TAKEOFF' if s=='TAKEOFF' and self.alt<15 else 'FLIGHT')
            speed=7 if s in ('CRUISE','ORBIT','TURN') else 0
            theta=t*(.08 if s in ('ORBIT','TURN') else .025)
            tx=speed*math.cos(theta); ty=speed*math.sin(theta)
            if self.returning:
                tx=max(-8,min(8,-self.x*.12)); ty=max(-8,min(8,-self.y*.12))
                if math.hypot(self.x,self.y)<1: self.returning=False; self.scenario='LANDING'
            if self.mode=='POSITION HOLD': tx=ty=0
            tx+=self.controls['pitch']*.08; ty+=self.controls['roll']*.08
            tz={'CLIMB':2,'DESCENT':-2,'LANDING':-3,'TAKEOFF':3 if self.alt<30 else 0}.get(s,.3*math.sin(t*.2))
            if self.mode=='ALTITUDE HOLD': tz=0
            if self.mode=='MANUAL' and s not in ('LANDING','TAKEOFF'): tz+=(self.throttle-50)*.06
            self.vx+=(tx-self.vx)*min(1,dt*1.5); self.vy+=(ty-self.vy)*min(1,dt*1.5); self.vz+=(tz-self.vz)*min(1,dt*2)
            self.x+=self.vx*dt; self.y+=self.vy*dt; self.alt=max(0,self.alt+self.vz*dt)
            if self.alt<=0 and s in ('LANDING','DESCENT'):
                self.armed=False; self.state='LANDED'; self.vx=self.vy=self.vz=0; self.throttle=0
            target_roll=4*math.sin(t*.5)+self.controls['roll']*.25
            target_pitch=2*math.sin(t*.4)+self.controls['pitch']*.25
            self.roll+=(target_roll-self.roll)*min(1,dt*3)
            self.pitch+=(target_pitch-self.pitch)*min(1,dt*3)
            self.yaw=(self.yaw+dt*(3+ self.controls['yaw']*.4))%360
            self.battery=max(0,self.battery-dt*(.018+self.throttle*.0003+(2.5 if s=='LOW BATTERY' else 0)))
        else: self.vx=self.vy=self.vz=0
        self.acc=tuple((v-o)/dt + (9.81 if i==2 else 0)+self.rng.gauss(0,.015) for i,(v,o) in enumerate(zip((self.vx,self.vy,self.vz),old)))
        self.gyro=((self.roll-angles[0])/dt,(self.pitch-angles[1])/dt,((self.yaw-angles[2]+180)%360-180)/dt)
        target_rssi=-104 if s=='COMMUNICATION FAILURE' else -62+3*math.sin(t*.13)
        self.rssi+=(target_rssi-self.rssi)*min(1,dt*.8)
        self.loss+=( (28 if s=='COMMUNICATION FAILURE' else 0)-self.loss)*min(1,dt)
        if self.rng.random()<self.loss/100: self.lost+=1
        self.gps_elapsed+=dt
        if self.gps_elapsed>=1:
            self.gps_elapsed-=1
            self.satellites=max(0,self.satellites-2) if s=='GPS FAILURE' else min(14,self.satellites+1)
        self.temp+=((85 if s=='SENSOR ANOMALY' else 32+3*math.sin(t*.1))-self.temp)*min(1,dt*.3)
        if s=='SENSOR ANOMALY': self.gyro=tuple(v+20*math.sin(t*8+i) for i,v in enumerate(self.gyro))
        return self.get_telemetry()
    def get_telemetry(self):
        ts=(self.epoch+timedelta(seconds=self.time)).isoformat()
        return Telemetry(timestamp=ts,sim_time=round(self.time,6),sequence=self.seq,
            position={'lat':HOME[0]+self.y/111320,'lon':HOME[1]+self.x/(111320*math.cos(math.radians(HOME[0]))),'alt':self.alt,'x':self.x,'y':self.y},
            velocity=dict(zip('xyz',(self.vx,self.vy,self.vz))),acceleration=dict(zip('xyz',self.acc)),gyro=dict(zip('xyz',self.gyro)),
            orientation={'roll':self.roll,'pitch':self.pitch,'yaw':self.yaw},battery={'percentage':self.battery,'voltage':12+4.2*self.battery/100,'current':(3+self.throttle*.15) if self.armed else .4},
            gps={'satellites':self.satellites,'fix':'3D' if self.satellites>=6 else ('2D' if self.satellites>=3 else 'NO FIX'),'hdop':1.1 if self.satellites>=6 else 9.9},
            rssi=self.rssi,temperature=self.temp,throttle=self.throttle,rate=self.settings.rate,packet_loss=self.loss,packets_lost=self.lost,latency=12+self.loss*4,
            state=self.state,mode=self.mode,armed=self.armed,health='CRITICAL' if self.battery<15 or self.satellites<3 or self.state=='EMERGENCY' else 'OK',scenario=self.scenario,paused=self.paused,
            detections=[{'class':'Drone','confidence':.92,'bbox':[.35+.12*math.sin(self.time*.3),.32,.16,.16],'timestamp':ts,'track_id':1},{'class':'Vehicle','confidence':.88,'bbox':[.72,.63,.13,.12],'timestamp':ts,'track_id':2}])
