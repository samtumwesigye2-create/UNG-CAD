const http = require("http");
const fs = require("fs");
const path = require("path");
const PORT = Number(process.env.PORT || 3000);
const ROOT = __dirname;
const allowed = new Set(["public","construction-takeoff","manufacturing","ung-cad-3d"]);
const types = {".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8",".json":"application/json; charset=utf-8",".svg":"image/svg+xml",".png":"image/png",".jpg":"image/jpeg",".jpeg":"image/jpeg",".stl":"model/stl",".wasm":"application/wasm"};
http.createServer((req,res)=>{
  const pathname = (req.url || "/").split("?")[0];
  if(pathname === "/health") {res.writeHead(200,{"content-type":"application/json"});return res.end(JSON.stringify({ok:true,service:"UNG-CAD"}));}
  let decoded;
  try {decoded = decodeURIComponent(pathname);} catch {res.writeHead(400);return res.end("Bad request");}
  if(decoded.includes("\\") || decoded.includes("\0")) {res.writeHead(400);return res.end("Bad request");}
  const parts = decoded.split("/").filter(Boolean);
  if(parts.some(p=>p==="." || p==="..")) {res.writeHead(403);return res.end("Forbidden");}
  const route = parts.length ? parts : ["public","index.html"];
  if(!allowed.has(route[0])) {res.writeHead(404);return res.end("Not found");}
  const file = path.resolve(ROOT,...route);
  const base = path.resolve(ROOT,route[0]);
  if(file!==base && !file.startsWith(base+path.sep)) {res.writeHead(403);return res.end("Forbidden");}
  fs.stat(file,(err,stat)=>{
    const target = !err && stat.isDirectory()?path.join(file,"index.html"):file;
    fs.readFile(target,(e,data)=>{
      if(e) {res.writeHead(404,{"content-type":"text/plain; charset=utf-8"});return res.end("Not found");}
      res.writeHead(200,{"content-type":types[path.extname(target).toLowerCase()]||"application/octet-stream","x-content-type-options":"nosniff"});
      res.end(data);
    });
  });
}).listen(PORT,"0.0.0.0",()=>console.log("UNG-CAD listening on",PORT));
