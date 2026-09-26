const fs=require('fs'),assert=require('assert'),path=require('path');
const root=path.join(__dirname,'..');
const pages=['studio.html','drafting.html','viewer.html','manufacturing.html'];
for(const p of pages){const s=fs.readFileSync(path.join(root,p),'utf8');assert.ok(/<!doctype html>/i.test(s),p+' missing doctype');assert.ok(!s.includes('undefinedundefined'),p+' contains broken generated text');}
const studio=fs.readFileSync(path.join(root,'studio.html'),'utf8');
for(const x of ['./drafting.html','./viewer.html'])assert.ok(studio.includes(x),'Studio route missing '+x);
const viewer=fs.readFileSync(path.join(root,'viewer.html'),'utf8');
assert.ok(viewer.includes('./professional-core.js'));assert.ok(viewer.includes('./professional-ui.js'));
const drafting=fs.readFileSync(path.join(root,'drafting.html'),'utf8');
assert.ok(drafting.includes('./professional-core.js'));assert.ok(drafting.includes('./drafting-professional.js'));
console.log('workspace smoke tests passed');