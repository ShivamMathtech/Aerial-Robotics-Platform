export async function api<T=any>(path:string,method='GET',body?:unknown):Promise<T>{
  const r=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json','X-API-Key':sessionStorage.getItem('api_key')||''},body:body===undefined?undefined:JSON.stringify(body)});
  if(!r.ok){let message;try{message=JSON.stringify((await r.json()).detail)}catch{message=r.statusText}throw new Error(message||`HTTP ${r.status}`)}
  return r.json();
}
export function saveFile(name:string,content:BlobPart,type='application/json'){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
export async function exportSession(id:string,format:string){const r=await fetch(`/api/sessions/${id}/export?format=${format}`,{headers:{'X-API-Key':sessionStorage.getItem('api_key')||''}});if(!r.ok)throw new Error('Export failed');saveFile(`session-${id}.${format}`,await r.blob(),format==='csv'?'text/csv':'application/json')}
export function flatten(object:Record<string,any>,prefix=''):Record<string,any>{return Object.assign({},...Object.entries(object).map(([k,v])=>v&&typeof v==='object'&&!Array.isArray(v)?flatten(v,prefix+k+'.'):{[prefix+k]:Array.isArray(v)?JSON.stringify(v):v}))}
