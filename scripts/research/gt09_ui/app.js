import {labels,colors,UNREVIEWED,runsOf,pixelsOf,countsOf,brush,rectangle,polygon,History} from './model.js';
const $=id=>document.getElementById(id),token=document.querySelector('meta[name=review-token]').content;
let packet,state,current,pixels,history,dirty=false,space=false,drag=null,points=[],busy=false;
const source=$('source'),overlay=$('overlay'),guide=$('guide'),view=$('viewport');
const sc=source.getContext('2d'),oc=overlay.getContext('2d'),gc=guide.getContext('2d');
async function api(path,data){const r=await fetch(path,{method:data===undefined?'GET':'POST',headers:data===undefined?{}:{'Content-Type':'application/json','X-Review-Token':token},body:data===undefined?undefined:JSON.stringify(data)});const result=await r.json();if(!r.ok)throw Error(result.error||r.statusText);return result;}
function status(s){$('status').textContent=s;}
function ask(message){return new Promise(resolve=>{const dialog=$('confirmDialog');$('confirmText').textContent=message;const done=value=>{dialog.close();resolve(value);};$('confirmYes').onclick=()=>done(true);$('confirmNo').onclick=()=>done(false);dialog.oncancel=e=>{e.preventDefault();done(false);};dialog.showModal();});}
function selected(){return Number(document.querySelector('[name=label]:checked').value);}
function remember(){if(!current)return;state.cases[current.case_id]={case_id:current.case_id,image_sha256:current.sha256,width:current.width,height:current.height,runs:runsOf(pixels,current.width,current.height),finalized:$('finalState').dataset.finalized==='true',uncertainty_acknowledged:$('ack').checked};}
function changed(){dirty=true;$('ack').checked=false;$('finalState').dataset.finalized='false';draw();status('저장하지 않은 수동 주석이 있습니다.');}
function draw(){
  const data=oc.createImageData(current.width,current.height);
  for(let i=0;i<pixels.length;i++) {const v=pixels[i];if(v===UNREVIEWED)continue;data.data.set([...colors[v],255],i*4);}
  oc.putImageData(data,0,0);overlay.style.opacity=Number($('opacity').value)/100;
  // Keep the interaction surface active even when showing only the source.
  overlay.style.visibility='visible';if(!$('show').checked)overlay.style.opacity=0;
  const counts=countsOf(pixels),names=['TEXT 텍스트','NON_TEXT 비텍스트','MIXED 혼합','UNKNOWN 불확실','미검토'];
  $('coverage').replaceChildren(...counts.map((n,i)=>{const d=document.createElement('div');d.textContent=`${names[i]}: ${n.toLocaleString()} px (${(100*n/pixels.length).toFixed(2)}%)`;return d;}));
  $('finalize').disabled=counts[UNREVIEWED]>0||!$('ack').checked;
  $('finalState').textContent=$('finalState').dataset.finalized==='true'?'소유자가 확정함 — 불확실 픽셀은 그대로 보존':'미확정';
  $('undo').disabled=!history.undo.length;$('redo').disabled=!history.redo.length;
  drawGuide();
}
function drawGuide(){gc.clearRect(0,0,guide.width,guide.height);gc.strokeStyle='#00b065';gc.lineWidth=1;gc.setLineDash([3,2]);
 if(points.length){gc.beginPath();gc.moveTo(points[0].x+.5,points[0].y+.5);for(const p of points.slice(1))gc.lineTo(p.x+.5,p.y+.5);gc.stroke();for(const p of points)gc.strokeRect(p.x-1,p.y-1,3,3);}
 if(drag?.tool==='rect'){const a=drag.start,b=drag.last;gc.strokeRect(Math.min(a.x,b.x),Math.min(a.y,b.y),Math.abs(a.x-b.x)+1,Math.abs(a.y-b.y)+1);}
}
function zoom(){const scale=Number($('zoom').value)/100;$('zoomValue').textContent=`${Math.round(scale*100)}%`;for(const c of [source,overlay,guide]){c.style.width=current.width*scale+'px';c.style.height=current.height*scale+'px';}$('stage').style.width=current.width*scale+'px';$('stage').style.height=current.height*scale+'px';}
function xy(e){const r=overlay.getBoundingClientRect();return{x:Math.floor((e.clientX-r.left)*current.width/r.width),y:Math.floor((e.clientY-r.top)*current.height/r.height)};}
function inBounds(p){return p.x>=0&&p.y>=0&&p.x<current.width&&p.y<current.height;}
async function loadCase(id){
  const next=packet.cases.find(c=>c.case_id===id);
  const old=state.cases[id];
  const nextPixels=old?pixelsOf(old.runs,next.width,next.height):new Uint8Array(next.width*next.height).fill(UNREVIEWED);
  const image=new Image();image.src='/case/'+id;await image.decode();
  // Commit the switch only after the original image successfully loads.
  current=next;pixels=nextPixels;points=[];drag=null;history=new History();
  for(const c of [source,overlay,guide]){c.width=current.width;c.height=current.height;}
  sc.drawImage(image,0,0);
  $('identity').textContent=`${current.case_id}\n${current.width} × ${current.height} px · 해시 ${current.sha256}`;
  $('finalState').dataset.finalized=String(old?.finalized===true);$('ack').checked=old?.uncertainty_acknowledged===true;zoom();draw();view.scrollTo(0,0);
}
async function save(){
  if(points.length)throw Error('다각형을 먼저 적용하거나 선택 취소하세요. 꼭짓점은 아직 픽셀 주석이 아닙니다.');
  remember();state=await api('/api/state',state);dirty=false;
  status('로컬 디스크에 저장했습니다. 브라우저를 다시 열어 이어할 수 있습니다.');
}
function action(fn){return async(...args)=>{
  if(busy)return;busy=true;document.querySelector('aside').inert=true;
  try{await fn(...args);}catch(e){if(current)$('cases').value=current.case_id;status('오류: '+e.message);}
  finally{busy=false;document.querySelector('aside').inert=!current;}
};}
$('save').onclick=action(save);
$('cases').onchange=action(async()=>{await save();await loadCase($('cases').value);});
$('unknown').onclick=action(async()=>{if(await ask('이 사례 전체를 직접 UNKNOWN으로 지정할까요? 완료된 텍스트 관찰을 의미하지 않습니다.')){history.push(pixels);pixels.fill(3);changed();}});
$('undo').onclick=()=>{pixels=history.back(pixels);changed();};$('redo').onclick=()=>{pixels=history.forward(pixels);changed();};
$('cancel').onclick=()=>{points=[];drawGuide();};
$('polyDone').onclick=()=>{if(points.length<3){status('꼭짓점을 세 개 이상 클릭하세요.');return;}history.push(pixels);polygon(pixels,current.width,current.height,points,selected());points=[];changed();};
$('tool').onchange=()=>{if(points.length){$('tool').value='polygon';status('다각형을 먼저 적용하거나 선택 취소하세요.');return;}drawGuide();overlay.style.cursor=$('tool').value==='pan'?'grab':'crosshair';};
$('zoom').oninput=zoom;$('native').onclick=()=>{$('zoom').value=100;zoom();};$('opacity').oninput=draw;$('show').onchange=draw;$('ack').onchange=()=>{dirty=true;if(!$('ack').checked)$('finalState').dataset.finalized='false';draw();};
$('finalize').onclick=action(async()=>{if(points.length)throw Error('다각형을 먼저 적용하거나 선택 취소하세요.');const c=countsOf(pixels);if(c[4]||!$('ack').checked)throw Error('커버리지 확인이 필요합니다');if(!await ask(`UNKNOWN ${c[3]} px, MIXED ${c[2]} px. 불확실성을 그대로 남겨 소유자 검토를 확정할까요? 독립 정답이나 합성 승인이 아닙니다.`))return;$('finalState').dataset.finalized='true';dirty=true;draw();await save();});
$('export').onclick=action(async()=>{await save();const r=await fetch('/api/export',{method:'POST',headers:{'X-Review-Token':token}});if(!r.ok)throw Error((await r.json()).error);const data=await r.blob();const url=URL.createObjectURL(data),a=document.createElement('a');a.href=url;a.download='gt09-owner-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('검증된 OWNER_REVIEW RLE를 내보냈습니다. 서버에도 해시 이름으로 별도 보존했습니다.');});
overlay.onpointerdown=e=>{if(busy||!current)return;if(e.button!==0&&e.button!==1)return;e.preventDefault();overlay.focus({preventScroll:true});const p=xy(e),tool=(space||e.button===1)?'pan':$('tool').value;
 if(tool==='pan'){drag={tool,x:e.clientX,y:e.clientY,sx:view.scrollLeft,sy:view.scrollTop};overlay.setPointerCapture(e.pointerId);return;}
 if(!inBounds(p))return;
 if(tool==='polygon'){points.push(p);drawGuide();return;}
 if(tool==='brush'){history.push(pixels);brush(pixels,current.width,current.height,p,p,Math.min(40,Math.max(0,Math.floor(Number($('radius').value)||0))),selected());changed();}
 drag={tool,start:p,last:p};overlay.setPointerCapture(e.pointerId);
};
overlay.onpointermove=e=>{if(busy||!current)return;const p=xy(e);if(!drag)return;if(drag.tool==='pan'){view.scrollLeft=drag.sx-(e.clientX-drag.x);view.scrollTop=drag.sy-(e.clientY-drag.y);return;}
 const bounded={x:Math.max(0,Math.min(current.width-1,p.x)),y:Math.max(0,Math.min(current.height-1,p.y))};
 if(drag.tool==='brush'){brush(pixels,current.width,current.height,drag.last,bounded,Math.min(40,Math.max(0,Math.floor(Number($('radius').value)||0))),selected());changed();}drag.last=bounded;drawGuide();};
function release(){if(!drag)return;if(drag.tool==='rect'){history.push(pixels);rectangle(pixels,current.width,current.height,drag.start,drag.last,selected());changed();}drag=null;drawGuide();}
overlay.onpointerup=release;overlay.onpointercancel=()=>{drag=null;drawGuide();};
window.addEventListener('keydown',e=>{if(busy)return;if(['TEXTAREA','SELECT'].includes(e.target.tagName)||(e.target.tagName==='INPUT'&&!['radio','checkbox','range'].includes(e.target.type)))return;if(e.code==='Space'){space=true;e.preventDefault();}if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='z'){e.preventDefault();(e.shiftKey?$('redo'):$('undo')).click();}if(e.key==='Escape'){points=[];drawGuide();}});
window.addEventListener('keyup',e=>{if(e.code==='Space')space=false;});
window.addEventListener('beforeunload',e=>{if(dirty||points.length){e.preventDefault();e.returnValue='';}});
action(async()=>{packet=await api('/api/packet');state=await api('/api/state');
 for(let i=0;i<labels.length-1;i++){const label=document.createElement('label'),radio=document.createElement('input'),swatch=document.createElement('span');radio.type='radio';radio.name='label';radio.value=i;radio.checked=i===0;swatch.className='swatch';swatch.style.background=`rgb(${colors[i]})`;label.append(radio,swatch,document.createTextNode(labels[i]));$('legend').append(label);}
 for(let i=0;i<packet.cases.length;i++){const c=packet.cases[i],o=document.createElement('option');o.value=c.case_id;o.textContent=`${i+1} / 5 · ${c.case_id.slice(0,8)}`;$('cases').append(o);}$('cases').disabled=false;await loadCase(packet.cases[0].case_id);document.querySelector('aside').inert=false;status('원본 해시 확인 완료. 분류는 사용자가 직접 지정해야 합니다. 저장된 검토가 있으면 복원됩니다.');
})().catch(e=>status(e.message));
