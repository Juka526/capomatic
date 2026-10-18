import {test} from 'node:test';
import assert from 'node:assert/strict';
import {runsOf,pixelsOf,countsOf,brush,rectangle,polygon,History} from '../scripts/research/gt09_ui/model.js';
test('lossless deterministic canonical RLE; missing/overlap/float rejected',()=>{
 const p=Uint8Array.from([0,0,1,2,3,4,4,4]);const r=runsOf(p,4,2);
 assert.deepEqual(pixelsOf(r,4,2),p);assert.deepEqual(runsOf(pixelsOf(r,4,2),4,2),r);
 assert.throws(()=>pixelsOf([[0,0,4,'TEXT']],4,2));
 assert.throws(()=>pixelsOf([[0,0,4,'TEXT'],[0,3,4,'TEXT']],4,2));
 assert.throws(()=>pixelsOf([[0,0.5,4,'TEXT']],4,1));
});
test('brush interpolates manual stroke and clips to image without source access',()=>{
 const p=new Uint8Array(25).fill(4);brush(p,5,5,{x:0,y:0},{x:4,y:4},0,0);
 assert.equal(countsOf(p)[0],5);assert.equal(p[1],4);
 brush(p,5,5,{x:0,y:0},{x:0,y:0},1,1);assert.equal(countsOf(p)[1],3);
});
test('rectangle and polygon include integer centers and boundary, not neighboring pixels',()=>{
 const p=new Uint8Array(25).fill(4);rectangle(p,5,5,{x:1,y:1},{x:3,y:3},1);assert.equal(countsOf(p)[1],9);
 polygon(p,5,5,[{x:0,y:0},{x:2,y:0},{x:0,y:2}],2);assert.equal(countsOf(p)[2],6);assert.equal(p[24],4);
});
test('undo/redo exact arrays and new edit clears redo',()=>{
 const h=new History();let p=new Uint8Array(4).fill(4);h.push(p);p.fill(0);p=h.back(p);assert.deepEqual([...p],[4,4,4,4]);p=h.forward(p);assert.deepEqual([...p],[0,0,0,0]);p=h.back(p);h.push(p);assert.equal(h.redo.length,0);
});
