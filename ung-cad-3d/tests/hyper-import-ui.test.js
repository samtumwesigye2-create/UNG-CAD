const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'hyper.html'), 'utf8');

function mustContain(text, label) {
  if (!html.includes(text)) {
    console.error(`FAIL: missing ${label}: ${text}`);
    process.exitCode = 1;
  }
}

mustContain('id="import3d"', '3D file input');
mustContain('accept=".stl,.obj,.glb,.gltf"', 'supported import file types');
mustContain('Import 3D File', 'visible import control');
mustContain('id="returnHyper"', 'return-to-hyper control');
mustContain("STLLoader", 'STL loader');
mustContain("OBJLoader", 'OBJ loader');
mustContain("GLTFLoader", 'GLTF/GLB loader');
mustContain('fitImportedModel', 'camera fit helper');
mustContain('renderImportedFile', 'import render handler');

if (!process.exitCode) console.log('hyper import UI contract passed');
