const fs=require('fs'),assert=require('assert'),path=require('path');
const src=fs.readFileSync(path.join(__dirname,'..','viewer.js'),'utf8');
assert.ok(src.includes('window.addEventListener("ung:4d-time"'));
assert.ok(src.includes('function apply4DGeometryTime'));
assert.ok(src.includes('window.__ung4dGeometry'));
assert.ok(src.includes('o.mesh.position.copy(b.position)'));
assert.ok(src.includes('o.mesh.rotation.copy(b.rotation)'));
assert.ok(src.includes('o.mesh.scale.copy(b.scale)'));
console.log('4D geometry playback contract OK');
