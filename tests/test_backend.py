import math
import time
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient
from app.main import create_app
from app.simulator import SimulatorAdapter, SCENARIOS
from app.schemas import Settings, Telemetry, CommandIn
from app.services import evaluate_alerts, validate_command

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app('sqlite:///'+str(tmp_path/'test.db'))) as c: yield c

def test_deterministic_trajectory_and_telemetry():
    a=SimulatorAdapter(Settings(seed=123)); b=SimulatorAdapter(Settings(seed=123))
    for _ in range(500): assert a.step(.02).model_dump()==b.step(.02).model_dump()
    assert a.x>10 and a.battery<78
    assert all(math.isfinite(n) for n in (a.x,a.y,a.alt,a.roll))

def test_pause_and_emergency_latch():
    s=SimulatorAdapter();s.send_command('PAUSE');start=s.get_telemetry();assert s.step(.1)==start
    s.send_command('EMERGENCY_STOP');assert validate_command(s,CommandIn(type='ARM'))
    s.send_command('RESET');assert s.state=='FLIGHT'

@pytest.mark.parametrize('scenario',SCENARIOS)
def test_scenarios_valid(scenario):
    s=SimulatorAdapter();s.send_command('SET_SCENARIO',scenario)
    for _ in range(120): data=s.step(.1)
    assert Telemetry.model_validate(data.model_dump())
    if scenario=='GPS FAILURE':assert data.gps.fix=='NO FIX'
    if scenario=='COMMUNICATION FAILURE':assert data.packet_loss>20
    if scenario=='SENSOR ANOMALY':assert data.temperature>70

def test_landing_and_return_home():
    s=SimulatorAdapter();s.alt=3;s.send_command('LAND')
    for _ in range(100):s.step(.1)
    assert s.alt==0 and not s.armed and s.state=='LANDED'
    s.reset();s.x=40;s.y=20;s.send_command('RTH')
    for _ in range(800):s.step(.1)
    assert math.hypot(s.x,s.y)<2

def test_alert_severity_and_battery():
    s=SimulatorAdapter();s.battery=25
    assert evaluate_alerts(s.get_telemetry(),Settings())['battery'][0]=='WARNING'
    s.battery=12; s.satellites=0
    rules=evaluate_alerts(s.get_telemetry(),Settings())
    assert rules['battery'][0]=='CRITICAL' and rules['gps'][0]=='CRITICAL'

def test_invalid_telemetry():
    d=SimulatorAdapter().get_telemetry().model_dump();d['battery']['percentage']=101
    with pytest.raises(ValidationError):Telemetry.model_validate(d)

@pytest.mark.parametrize('body',[{'type':'SET_CONTROL','value':{'throttle':101}}, {'type':'SET_CONTROL','value':{'bogus':2}}, {'type':'SET_MODE','value':'INVALID'},{'type':'DISARM'}])
def test_commands_reject(client,body):
    r=client.post('/api/commands',json=body);assert r.status_code==200;assert r.json()['status']=='REJECTED'

def test_api_and_websocket(client):
    assert client.get('/api/vehicles').json()[0]['id']=='DR-001'
    assert client.get('/api/vehicles/missing').status_code==404
    assert client.get('/api/telemetry/history?limit=0').status_code==422
    with client.websocket_connect('/ws/telemetry') as ws:
        first=ws.receive_json(); second=ws.receive_json()
        assert first['type']=='telemetry' and second['data']['sequence']>first['data']['sequence']
    with client.websocket_connect('/ws/commands') as ws:
        ws.send_json({'type':'PAUSE'})
        assert ws.receive_json()['status']=='ACCEPTED'
    assert client.post('/api/commands',json={'type':'RESUME'}).json()['status']=='ACCEPTED'

def test_record_export_replay_and_missions(client):
    m=client.post('/api/missions',json={'name':'Integration flight'}).json()
    assert client.patch('/api/missions/'+m['id'],json={'status':'COMPLETED'}).status_code==409
    assert client.patch('/api/missions/'+m['id'],json={'status':'RUNNING'}).status_code==200
    wp=client.post(f'/api/missions/{m["id"]}/waypoints',json={'lat':30.32,'lon':78.03,'altitude':80}).json()
    assert client.delete('/api/waypoints/'+wp['id']).status_code==200
    sid=client.post('/api/sessions/start?mission_id='+m['id']).json()['id']
    assert client.post('/api/sessions/start').status_code==409
    with client.websocket_connect('/ws/telemetry') as ws:
        for _ in range(5):ws.receive_json()
    client.post('/api/commands',json={'type':'SET_MODE','value':'AUTO'})
    client.post('/api/sessions/pause');points=client.get(f'/api/sessions/{sid}/points').json();assert len(points)>5
    with client.websocket_connect('/ws/telemetry') as ws:
        for _ in range(3):ws.receive_json()
    assert len(client.get(f'/api/sessions/{sid}/points').json())==len(points)
    client.post('/api/sessions/resume')
    with client.websocket_connect('/ws/telemetry') as ws:
        for _ in range(3):ws.receive_json()
    client.post('/api/sessions/stop')
    all_points=client.get(f'/api/sessions/{sid}/points').json()
    exported=client.get(f'/api/sessions/{sid}/export').json()
    assert exported['telemetry']==all_points and len(all_points)>len(points)
    assert exported['commands'][0]['type']=='SET_MODE'
    assert exported['events']
    assert 'position.lat' in client.get(f'/api/sessions/{sid}/export?format=csv').text
    assert client.get('/api/sessions').json()[0]['samples']==len(all_points)

def test_settings_validation_and_auth(tmp_path,monkeypatch):
    monkeypatch.setenv('API_KEY','test-only-key')
    with TestClient(create_app('sqlite:///'+str(tmp_path/'auth.db'))) as c:
        assert c.get('/api/telemetry/latest').status_code==401
        assert c.get('/api/telemetry/latest',headers={'X-API-Key':'test-only-key'}).status_code==200
        assert c.put('/api/settings',headers={'X-API-Key':'test-only-key'},json={'rate':500}).status_code==422
        with c.websocket_connect('/ws/telemetry') as ws:
            ws.send_json({'api_key':'test-only-key'});assert ws.receive_json()['type']=='telemetry'

def test_alert_ack_and_resolution(client):
    client.post('/api/commands',json={'type':'EMERGENCY_STOP'})
    deadline=time.monotonic()+3
    alerts=[]
    while time.monotonic()<deadline:
        alerts=client.get('/api/alerts').json()
        if alerts:break
        time.sleep(.05)
    assert alerts[0]['severity']=='CRITICAL'
    assert client.post('/api/alerts/'+alerts[0]['id']+'/ack').json()['acknowledged']
