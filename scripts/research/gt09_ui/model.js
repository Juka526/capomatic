// Native crop-local integer pixel centers; no image-content analysis.
export const labels = ['TEXT', 'NON_TEXT', 'MIXED', 'UNKNOWN', 'UNREVIEWED'];
export const colors = [[240,60,70], [30,140,230], [180,70,210], [245,180,25], [0,0,0]];
export const UNREVIEWED = 4;
export function runsOf(pixels, w, h) {
  if (pixels.length !== w*h) throw Error('크기 불일치');
  const runs=[];
  for(let y=0;y<h;y++) for(let x=0;x<w;) {
    const left=x, v=pixels[y*w+x];
    if(!Number.isInteger(v)||v<0||v>=labels.length) throw Error('범주 오류');
    while(x<w&&pixels[y*w+x]===v) x++;
    runs.push([y,left,x,labels[v]]);
  }
  return runs;
}
export function pixelsOf(runs,w,h) {
  const p=new Uint8Array(w*h); let next=0;
  for(const [y,l,r,label] of runs) {
    const v=labels.indexOf(label);
    if(![y,l,r].every(Number.isInteger)||v<0||y<0||y>=h||l<0||l>=r||r>w||y*w+l!==next) throw Error('누락/중복/범위 오류');
    p.fill(v,y*w+l,y*w+r);next=y*w+r;
  }
  if(next!==p.length) throw Error('픽셀 누락');
  return p;
}
export function countsOf(p) {const c=[0,0,0,0,0];for(const v of p)c[v]++;return c;}
export function brush(p,w,h,a,b,r,v) {
  // Interpolate only the owner's pointer stroke, never source intensity.
  const steps=Math.max(Math.abs(b.x-a.x),Math.abs(b.y-a.y),1);
  for(let t=0;t<=steps;t++) {
    const x=Math.round(a.x+(b.x-a.x)*t/steps), y=Math.round(a.y+(b.y-a.y)*t/steps);
    for(let yy=Math.max(0,y-r);yy<=Math.min(h-1,y+r);yy++)
      for(let xx=Math.max(0,x-r);xx<=Math.min(w-1,x+r);xx++)
        if((xx-x)**2+(yy-y)**2<=r*r)p[yy*w+xx]=v;
  }
}
export function rectangle(p,w,h,a,b,v) {
  for(let y=Math.max(0,Math.min(a.y,b.y));y<=Math.min(h-1,Math.max(a.y,b.y));y++)
    for(let x=Math.max(0,Math.min(a.x,b.x));x<=Math.min(w-1,Math.max(a.x,b.x));x++)p[y*w+x]=v;
}
function contains(x,y,points) {
  let inside=false;
  for(let i=0,j=points.length-1;i<points.length;j=i++) {
    const a=points[j],b=points[i];
    const cross=(x-a.x)*(b.y-a.y)-(y-a.y)*(b.x-a.x);
    if(cross===0&&x>=Math.min(a.x,b.x)&&x<=Math.max(a.x,b.x)&&y>=Math.min(a.y,b.y)&&y<=Math.max(a.y,b.y))return true;
    if((a.y>y)!==(b.y>y)&&x<(b.x-a.x)*(y-a.y)/(b.y-a.y)+a.x)inside=!inside;
  }
  return inside;
}
export function polygon(p,w,h,points,v) {
  if(points.length<3)throw Error('세 꼭짓점 이상 필요');
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
  for(let y=Math.max(0,Math.min(...ys));y<=Math.min(h-1,Math.max(...ys));y++)
    for(let x=Math.max(0,Math.min(...xs));x<=Math.min(w-1,Math.max(...xs));x++)if(contains(x,y,points))p[y*w+x]=v;
}
export class History {
  constructor(){this.undo=[];this.redo=[];}
  push(p){this.undo.push(p.slice());if(this.undo.length>50)this.undo.shift();this.redo=[];}
  back(p){if(!this.undo.length)return p;this.redo.push(p.slice());return this.undo.pop();}
  forward(p){if(!this.redo.length)return p;this.undo.push(p.slice());return this.redo.pop();}
}
