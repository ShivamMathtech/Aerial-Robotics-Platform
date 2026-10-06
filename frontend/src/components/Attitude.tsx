import {useEffect,useRef,useState} from 'react';
import * as THREE from 'three';
import type {Telemetry} from '../types';
export function Attitude({t}:{t:Telemetry|null}){const host=useRef<HTMLDivElement>(null);const value=useRef(t);value.current=t;const[error,setError]=useState('');
 useEffect(()=>{const el=host.current!;let renderer:THREE.WebGLRenderer;try{renderer=new THREE.WebGLRenderer({antialias:true,alpha:true})}catch{setError('WebGL unavailable. Enable browser hardware acceleration.');return}
 const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(42,1,.1,100);camera.position.set(4,3.8,5);camera.lookAt(0,0,0);renderer.setPixelRatio(Math.min(devicePixelRatio,2));el.appendChild(renderer.domElement);
 scene.add(new THREE.HemisphereLight(0xbdeaff,0x223344,3));const light=new THREE.DirectionalLight(0xffffff,3);light.position.set(3,5,2);scene.add(light);
 const grid=new THREE.GridHelper(10,20,0x225577,0x102f42);grid.position.y=-.8;scene.add(grid);scene.add(new THREE.AxesHelper(2.4));
 const drone=new THREE.Group();scene.add(drone);const material=new THREE.MeshStandardMaterial({color:0x5d8497,metalness:.7,roughness:.35});
 const body=new THREE.Mesh(new THREE.BoxGeometry(.85,.26,.6),material);drone.add(body);
 for(const angle of [Math.PI/4,-Math.PI/4]){const arm=new THREE.Mesh(new THREE.BoxGeometry(2.8,.10,.1),material);arm.rotation.y=angle;drone.add(arm)}
 const rotors:THREE.Mesh[]=[];
 for(const x of [-.95,.95])for(const z of [-.95,.95]){const motor=new THREE.Mesh(new THREE.CylinderGeometry(.13,.13,.3,12),new THREE.MeshStandardMaterial({color:z<0?0x00eeaa:0xff6544}));motor.position.set(x,.13,z);drone.add(motor);const rotor=new THREE.Mesh(new THREE.BoxGeometry(.78,.02,.09),new THREE.MeshStandardMaterial({color:0x8ed6ee,transparent:true,opacity:.7}));rotor.position.set(x,.3,z);rotors.push(rotor);drone.add(rotor)}
 let id=0;const target=new THREE.Quaternion();const animate=()=>{const v=value.current;if(v){target.setFromEuler(new THREE.Euler(THREE.MathUtils.degToRad(v.orientation.pitch),-THREE.MathUtils.degToRad(v.orientation.yaw),-THREE.MathUtils.degToRad(v.orientation.roll),'YXZ'));drone.quaternion.slerp(target,.13);if(v.armed&&!v.paused)rotors.forEach(r=>r.rotation.y+=.45)}renderer.render(scene,camera);id=requestAnimationFrame(animate)};
 const resize=()=>{const w=el.clientWidth,h=el.clientHeight;if(w&&h){renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix()}};const ro=new ResizeObserver(resize);ro.observe(el);resize();animate();
 return()=>{cancelAnimationFrame(id);ro.disconnect();scene.traverse(obj=>{if(obj instanceof THREE.Mesh){obj.geometry.dispose();const ms=Array.isArray(obj.material)?obj.material:[obj.material];ms.forEach(m=>m.dispose())}});renderer.dispose();el.removeChild(renderer.domElement)};
 },[]);
 return <div className="attitude-wrap"><div className="attitude" ref={host} data-testid="attitude-view"/>{error&&<div className="overlay-note">{error}</div>}<div className="attitude-values">{['roll','pitch','yaw'].map(k=><div key={k}>{k.toUpperCase()}<strong>{(t?.orientation[k as keyof Telemetry['orientation']]||0).toFixed(1)}°</strong></div>)}</div><span className="axis-note">X east · Y north · Z up</span></div>
}
