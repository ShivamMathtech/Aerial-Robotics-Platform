import {useEffect,useRef,useState} from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type {Telemetry,Waypoint} from '../types';
const HOME:L.LatLngTuple=[30.3165,78.0322];
export function FlightMap({t,history,waypoints,onWaypoint}:{t:Telemetry|null;history:Telemetry[];waypoints:Waypoint[];onWaypoint:(lat:number,lon:number)=>void}){
 const host=useRef<HTMLDivElement>(null);const map=useRef<L.Map>();const marker=useRef<L.Marker>();const path=useRef<L.Polyline>();const waypointLayer=useRef<L.LayerGroup>();const[follow,setFollow]=useState(true);const[tiles,setTiles]=useState(false);const[tileError,setTileError]=useState(false);const click=useRef(onWaypoint);click.current=onWaypoint;
 useEffect(()=>{const m=L.map(host.current!,{zoomControl:false,attributionControl:true}).setView(HOME,16);map.current=m;L.control.zoom({position:'topright'}).addTo(m);L.control.scale({imperial:false}).addTo(m);
 L.circle(HOME,{radius:500,color:'#2a92bc',weight:1,dashArray:'5 7',fillOpacity:.03}).addTo(m).bindTooltip('500 m visual geofence');
 L.circle([HOME[0]+.0025,HOME[1]-.002],{radius:90,color:'#f45362',weight:1,fillOpacity:.18}).addTo(m).bindTooltip('Demonstration no-fly zone');
 L.marker(HOME,{icon:L.divIcon({className:'home-marker',html:'H',iconSize:[20,20]})}).addTo(m).bindTooltip('Home');
 marker.current=L.marker(HOME,{icon:L.divIcon({className:'vehicle-marker',html:'<span>▲</span>',iconSize:[24,24]})}).addTo(m);path.current=L.polyline([],{color:'#00e69a',weight:2}).addTo(m);waypointLayer.current=L.layerGroup().addTo(m);
 m.on('click',(e:L.LeafletMouseEvent)=>click.current(e.latlng.lat,e.latlng.lng));m.on('dragstart',()=>setFollow(false));const ro=new ResizeObserver(()=>m.invalidateSize());ro.observe(host.current!);return()=>{ro.disconnect();m.remove()};},[]);
 useEffect(()=>{if(!t||!map.current)return;const position:L.LatLngTuple=[t.position.lat,t.position.lon];marker.current?.setLatLng(position);const element=marker.current?.getElement();if(element?.firstElementChild)(element.firstElementChild as HTMLElement).style.transform=`rotate(${t.orientation.yaw}deg)`;path.current?.setLatLngs(history.map(p=>[p.position.lat,p.position.lon]));if(follow)map.current.panTo(position,{animate:false})},[t,history,follow]);
 useEffect(()=>{waypointLayer.current?.clearLayers();waypoints.forEach((w,i)=>L.marker([w.lat,w.lon],{icon:L.divIcon({className:'waypoint-marker',html:String(i+1),iconSize:[18,18]})}).addTo(waypointLayer.current!).bindTooltip(`Waypoint ${i+1}: ${w.altitude} m`))},[waypoints]);
 useEffect(()=>{if(!tiles||!map.current)return;setTileError(false);const layer=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap contributors',maxZoom:19});layer.on('tileerror',()=>setTileError(true));layer.addTo(map.current);return()=>{layer.remove()}},[tiles]);
 return <><div className="map-toolbar"><button onClick={()=>{map.current?.setView(HOME,16);setFollow(false)}}>Home</button><button className={follow?'active':''} onClick={()=>setFollow(!follow)}>Follow</button><button onClick={()=>setTiles(!tiles)}>{tiles?'Offline grid':'Street map'}</button><span>N ↑ · click to add waypoint</span></div><div className="map" ref={host} data-testid="flight-map"/>{tileError&&<small>Map tiles unavailable; position and path remain active.</small>}</>
}
