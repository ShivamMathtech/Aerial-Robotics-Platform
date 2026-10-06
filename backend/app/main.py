import asyncio
import csv
import io
import json
import logging
import os
import secrets
import time
from collections import deque
from contextlib import asynccontextmanager
from uuid import uuid4
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, update, func
from pathlib import Path
from .models import *
from .schemas import CommandIn, MissionIn, MissionStatus, Settings, WaypointIn
from .simulator import SimulatorAdapter, HOME, SCENARIOS
from .services import evaluate_alerts, validate_command

load_dotenv()
logging.basicConfig(level=os.getenv('LOG_LEVEL','INFO'))
log=logging.getLogger('aerial')

def uid(): return str(uuid4())
def create_app(db_url=None):
    @asynccontextmanager
    async def lifespan(app):
        engine, factory=database(db_url)
        app.state.engine=engine; app.state.db=factory
        with factory.begin() as db:
            if not db.get(Vehicle,'DR-001'):
                db.add(Vehicle(id='DR-001',name='Virtual Research Quadrotor')); db.flush()
                for i in range(1,4): db.add(Camera(id=f'CAM-{i}',vehicle_id='DR-001',name=f'Camera {i}'))
            db.execute(update(TelemetrySession).where(TelemetrySession.status.in_(['RECORDING','PAUSED'])).values(status='INTERRUPTED',end_time=now()))
            db.execute(update(Alert).values(active=False))
            config=db.get(SystemConfiguration,'settings')
            settings=Settings.model_validate(config.data) if config else Settings()
        app.state.sim=SimulatorAdapter(settings); app.state.settings=settings
        app.state.latest=app.state.sim.get_telemetry().model_dump()
        app.state.history=deque(maxlen=30000); app.state.recording=None; app.state.record_paused=False
        app.state.clients={'telemetry':set(),'events':set(),'commands':set()}; app.state.active_alerts={}
        app.state.pending=[]; app.state.last_error=None
        app.state.task=asyncio.create_task(run())
        yield
        app.state.task.cancel()
        try: await app.state.task
        except asyncio.CancelledError: pass
        flush()
        if app.state.recording:
            with factory.begin() as db:
                row=db.get(TelemetrySession,app.state.recording); row.status='STOPPED'; row.end_time=now()
        engine.dispose()
    app=FastAPI(title='Aerial Robotics Platform',version='1.0.0',lifespan=lifespan)
    origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080').split(',')
    app.add_middleware(CORSMiddleware,allow_origins=origins,allow_methods=['GET','POST','PATCH','PUT','DELETE'],allow_headers=['Content-Type','X-API-Key'])
    key=os.getenv('API_KEY','')
    @app.middleware('http')
    async def authenticate(request:Request,call_next):
        if key and request.url.path.startswith('/api/') and not secrets.compare_digest(request.headers.get('X-API-Key',''),key):
            return Response(content='{"detail":"API key required"}',status_code=401,media_type='application/json')
        return await call_next(request)
    def publish(channel,data):
        for queue in list(app.state.clients[channel]):
            if queue.full(): queue.get_nowait()
            queue.put_nowait(data)
    def flush():
        if not app.state.pending: return
        batch=app.state.pending
        with app.state.db.begin() as db: db.add_all([TelemetryPoint(**p) for p in batch])
        app.state.pending=[]
    def event_record(kind,message,mission_id=None):
        with app.state.db.begin() as db:
            row=Event(session_id=app.state.recording,mission_id=mission_id,kind=kind,message=message); db.add(row); db.flush(); data=serialize(row)
        publish('events',{'type':'event',**data})
    def process_alerts(telemetry):
        rules=evaluate_alerts(telemetry,app.state.settings,app.state.sim.connected)
        active=app.state.active_alerts
        with app.state.db.begin() as db:
            for rule,old in list(active.items()):
                if rule not in rules or rules[rule][0]!=old[1]:
                    row=db.get(Alert,old[0]); row.active=False; del active[rule]
            for rule,(severity,message) in rules.items():
                if rule not in active:
                    row=Alert(id=uid(),rule=rule,severity=severity,message=message); db.add(row); db.flush()
                    active[rule]=(row.id,severity); publish('events',{'type':'alert',**serialize(row)})
                    db.add(Event(session_id=app.state.recording,kind='ALERT',message=message))
    async def run():
        last_alert=0.; last_flush=time.monotonic(); last_frame=0.
        while True:
            began=time.monotonic(); sim=app.state.sim
            try:
                telemetry=sim.step(app.state.settings.speed/app.state.settings.rate)
                data=telemetry.model_dump(); app.state.latest=data
                if sim.connected and not sim.paused:
                    app.state.history.append(data)
                    if app.state.recording and not app.state.record_paused:
                        app.state.pending.append({'session_id':app.state.recording,'sim_time':telemetry.sim_time,'data':data})
                if began-last_frame>=.1:
                    publish('telemetry',{'type':'telemetry','data':data,'server_time':now(),'recording':app.state.recording,'record_paused':app.state.record_paused,'sim_connected':sim.connected})
                    last_frame=began
                if began-last_alert>=1:
                    process_alerts(telemetry); last_alert=began
                    if app.state.recording and not app.state.record_paused and not sim.paused:
                        with app.state.db.begin() as db:
                            db.add_all([Detection(session_id=app.state.recording,camera_id='CAM-1',data=d) for d in data['detections']])
                if began-last_flush>=1: flush(); last_flush=began
                app.state.last_error=None
            except Exception as exc:
                log.exception('Telemetry pipeline failure'); app.state.last_error=str(exc)
            await asyncio.sleep(max(.001,1/app.state.settings.rate-(time.monotonic()-began)))
    def get_row(db,cls,identifier):
        row=db.get(cls,identifier)
        if row is None: raise HTTPException(404,'Not found')
        return row
    @app.get('/api/vehicles')
    async def vehicles():
        with app.state.db() as db: return [serialize(r) for r in db.scalars(select(Vehicle))]
    @app.get('/api/vehicles/{identifier}')
    async def vehicle(identifier:str):
        with app.state.db() as db: return serialize(get_row(db,Vehicle,identifier))
    @app.get('/api/telemetry/latest')
    async def latest(): return app.state.latest
    @app.get('/api/telemetry/history')
    async def history(limit:int=Query(1000,ge=1,le=30000)): return list(app.state.history)[-limit:]
    @app.get('/api/system/status')
    async def status():
        return {'simulation':True,**app.state.sim.get_status(),'recording':app.state.recording,'record_paused':app.state.record_paused,'pipeline_error':app.state.last_error,'home':HOME,'scenarios':SCENARIOS,'settings':app.state.settings.model_dump()}
    @app.get('/api/settings')
    async def settings(): return app.state.settings
    @app.put('/api/settings')
    async def save_settings(settings:Settings):
        with app.state.db.begin() as db: db.merge(SystemConfiguration(id='settings',data=settings.model_dump()))
        app.state.settings=settings; app.state.sim.settings=settings
        event_record('SETTINGS','Simulation settings updated; seed applies on reset')
        return settings
    def execute(command):
        error=validate_command(app.state.sim,command)
        with app.state.db.begin() as db:
            row=Command(id=uid(),session_id=app.state.recording,type=command.type,value=command.value,source=command.source,status='REJECTED' if error else 'ACCEPTED',error=error)
            db.add(row); db.flush(); result=serialize(row)
        if not error:
            app.state.sim.send_command(command.type,command.value)
            app.state.latest=app.state.sim.get_telemetry().model_dump()
            if command.type=='RESET': app.state.history.clear()
        event_record('COMMAND',f'{command.type}: {result["status"]}'+(f' — {error}' if error else ''))
        publish('commands',{'type':'command',**result})
        return result
    @app.post('/api/commands')
    async def command(body:CommandIn): return execute(body)
    @app.get('/api/commands')
    async def command_history():
        with app.state.db() as db: return [serialize(r) for r in db.scalars(select(Command).order_by(Command.timestamp.desc()).limit(100))]
    @app.post('/api/simulation/start')
    async def start(): app.state.sim.connect(); return execute(CommandIn(type='RESUME'))
    @app.post('/api/simulation/stop')
    async def stop(): app.state.sim.disconnect(); return execute(CommandIn(type='PAUSE'))
    @app.post('/api/simulation/reset')
    async def reset(): return execute(CommandIn(type='RESET'))
    @app.get('/api/alerts')
    async def alerts():
        with app.state.db() as db: return [serialize(r) for r in db.scalars(select(Alert).order_by(Alert.timestamp.desc()).limit(200))]
    @app.post('/api/alerts/{identifier}/ack')
    async def ack(identifier:str):
        with app.state.db.begin() as db:
            row=get_row(db,Alert,identifier); row.acknowledged=True; db.flush(); return serialize(row)
    @app.get('/api/events')
    async def events():
        with app.state.db() as db: return [serialize(r) for r in db.scalars(select(Event).order_by(Event.id.desc()).limit(200))]
    @app.get('/api/missions')
    async def missions():
        with app.state.db() as db: return [serialize(r) for r in db.scalars(select(Mission).order_by(Mission.start_time.desc()))]
    @app.post('/api/missions',status_code=201)
    async def add_mission(body:MissionIn):
        with app.state.db.begin() as db:
            row=Mission(id=uid(),vehicle_id='DR-001',**body.model_dump()); db.add(row); db.flush(); data=serialize(row)
        event_record('MISSION','Created '+body.name,data['id']); return data
    @app.patch('/api/missions/{identifier}')
    async def update_mission(identifier:str,body:MissionStatus):
        allowed={'PLANNED':{'RUNNING','ABORTED'},'RUNNING':{'PAUSED','COMPLETED','ABORTED'},'PAUSED':{'RUNNING','COMPLETED','ABORTED'},'COMPLETED':set(),'ABORTED':set()}
        with app.state.db.begin() as db:
            row=get_row(db,Mission,identifier)
            if body.status not in allowed[row.status]: raise HTTPException(409,'Invalid mission transition')
            row.status=body.status; db.flush(); data=serialize(row)
        event_record('MISSION',f'{data["name"]}: {body.status}',identifier); return data
    @app.get('/api/missions/{identifier}/timeline')
    async def timeline(identifier:str):
        with app.state.db() as db:
            get_row(db,Mission,identifier)
            return [serialize(r) for r in db.scalars(select(Event).where(Event.mission_id==identifier).order_by(Event.id))]
    @app.get('/api/missions/{identifier}/waypoints')
    async def waypoints(identifier:str):
        with app.state.db() as db:
            get_row(db,Mission,identifier)
            return [serialize(r) for r in db.scalars(select(Waypoint).where(Waypoint.mission_id==identifier))]
    @app.post('/api/missions/{identifier}/waypoints')
    async def add_waypoint(identifier:str,body:WaypointIn):
        with app.state.db.begin() as db:
            get_row(db,Mission,identifier); row=Waypoint(id=uid(),mission_id=identifier,**body.model_dump()); db.add(row); db.flush(); return serialize(row)
    @app.delete('/api/waypoints/{identifier}')
    async def delete_waypoint(identifier:str):
        with app.state.db.begin() as db: db.delete(get_row(db,Waypoint,identifier))
        return {'deleted':identifier}
    @app.get('/api/sessions')
    async def sessions():
        with app.state.db() as db:
            rows=db.execute(select(TelemetrySession,func.count(TelemetryPoint.id)).outerjoin(TelemetryPoint).group_by(TelemetrySession.id).order_by(TelemetrySession.start_time.desc())).all()
            return [{**serialize(r),'samples':count} for r,count in rows]
    @app.post('/api/sessions/start')
    async def record(mission_id:str|None=None):
        if app.state.recording: raise HTTPException(409,'Already recording')
        with app.state.db.begin() as db:
            if mission_id: get_row(db,Mission,mission_id)
            row=TelemetrySession(id=uid(),vehicle_id='DR-001',mission_id=mission_id); db.add(row); db.flush(); data=serialize(row)
        app.state.recording=data['id']; app.state.record_paused=False
        event_record('RECORDING','Recording started',mission_id); return data
    @app.post('/api/sessions/stop')
    async def stop_record():
        if not app.state.recording: raise HTTPException(409,'No active recording')
        flush(); event_record('RECORDING','Recording stopped')
        with app.state.db.begin() as db:
            row=db.get(TelemetrySession,app.state.recording); row.end_time=now(); row.status='STOPPED'; db.flush(); data=serialize(row)
        app.state.recording=None; app.state.record_paused=False; return data
    @app.post('/api/sessions/{action}')
    async def pause_record(action:str):
        if action not in ('pause','resume'): raise HTTPException(404,'Unknown action')
        if not app.state.recording: raise HTTPException(409,'No active recording')
        app.state.record_paused=action=='pause'
        with app.state.db.begin() as db: db.get(TelemetrySession,app.state.recording).status='PAUSED' if app.state.record_paused else 'RECORDING'
        event_record('RECORDING',action); return {'paused':app.state.record_paused}
    @app.get('/api/sessions/{identifier}/points')
    async def points(identifier:str,offset:int=Query(0,ge=0),limit:int=Query(5000,ge=1,le=10000)):
        flush()
        with app.state.db() as db:
            get_row(db,TelemetrySession,identifier)
            return [p.data for p in db.scalars(select(TelemetryPoint).where(TelemetryPoint.session_id==identifier).order_by(TelemetryPoint.id).offset(offset).limit(limit))]
    @app.get('/api/sessions/{identifier}/export')
    async def export(identifier:str,format:str=Query('json',pattern='^(json|csv)$')):
        flush()
        with app.state.db() as db:
            session=serialize(get_row(db,TelemetrySession,identifier))
            data=[p.data for p in db.scalars(select(TelemetryPoint).where(TelemetryPoint.session_id==identifier).order_by(TelemetryPoint.id))]
            commands=[serialize(r) for r in db.scalars(select(Command).where(Command.session_id==identifier))]
            events=[serialize(r) for r in db.scalars(select(Event).where(Event.session_id==identifier))]
            detections=[serialize(r) for r in db.scalars(select(Detection).where(Detection.session_id==identifier))]
        if format=='json': content=json.dumps({'session':session,'telemetry':data,'commands':commands,'events':events,'detections':detections}); media='application/json'
        else:
            def flatten(d,prefix=''):
                result={}
                for k,v in d.items():
                    if isinstance(v,dict): result.update(flatten(v,prefix+k+'.'))
                    else: result[prefix+k]=json.dumps(v) if isinstance(v,list) else v
                return result
            output=io.StringIO(); rows=[flatten(p) for p in data]
            writer=csv.DictWriter(output,fieldnames=list(rows[0]) if rows else ['timestamp']); writer.writeheader(); writer.writerows(rows)
            content=output.getvalue(); media='text/csv'
        return Response(content,media_type=media,headers={'Content-Disposition':f'attachment; filename="session-{identifier}.{format}"'})
    @app.websocket('/ws/{channel}')
    async def socket(ws:WebSocket,channel:str):
        if channel not in app.state.clients: await ws.close(code=1008); return
        origin=ws.headers.get('origin')
        if origin and origin not in origins and origin!=str(ws.url).split('/ws/')[0].replace('ws:','http:').replace('wss:','https:'):
            await ws.close(code=1008); return
        await ws.accept()
        if key:
            try:
                first=await asyncio.wait_for(ws.receive_json(),5)
                if not secrets.compare_digest(str(first.get('api_key','')),key): await ws.close(code=1008); return
            except Exception: await ws.close(code=1008); return
        queue=asyncio.Queue(maxsize=2 if channel=='telemetry' else 100)
        app.state.clients[channel].add(queue)
        async def send():
            while True:
                try: data=await asyncio.wait_for(queue.get(),5)
                except asyncio.TimeoutError: data={'type':'heartbeat','timestamp':now()}
                await ws.send_json(data)
        sender=asyncio.create_task(send())
        try:
            while True:
                data=await ws.receive_json()
                if channel=='commands' and data.get('type')!='ping':
                    try: execute(CommandIn.model_validate(data))
                    except ValueError as exc: queue.put_nowait({'type':'error','message':str(exc)})
        except (WebSocketDisconnect,RuntimeError): pass
        finally:
            sender.cancel(); app.state.clients[channel].discard(queue)
            try: await sender
            except (asyncio.CancelledError,WebSocketDisconnect,RuntimeError): pass
    dist=Path(__file__).resolve().parents[2]/'frontend'/'dist'
    if dist.exists():
        app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
        @app.get('/')
        def index(): return FileResponse(dist/'index.html')
    return app
app=create_app()
