const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = Number(process.env.PORT || 3000);
const ROOT = path.join(__dirname, "public");

const types = {
  ".html":"text/html; charset=utf-8",
  ".js":"text/javascript; charset=utf-8",
  ".css":"text/css; charset=utf-8",
  ".json":"application/json; charset=utf-8",
  ".svg":"image/svg+xml",
  ".png":"image/png",
  ".jpg":"image/jpeg",
  ".jpeg":"image/jpeg",
  ".stl":"model/stl"
};

http.createServer((req,res)=>{
  if (req.url === "/health") {
    res.writeHead(200, {"content-type":"application/json"});
    return res.end(JSON.stringify({ok:true,service:"UNG-CAD"}));
  }
  const raw = decodeURIComponent((req.url || "/").split("?")[0]);
  let rel = raw === "/" ? "index.html" : raw.replace(/^\/+/, "");
  let file = path.normalize(path.join(ROOT, rel));
  if (!file.startsWith(ROOT)) {
    res.writeHead(403); return res.end("Forbidden");
  }
  fs.stat(file,(err,stat)=>{
    if (!err && stat.isDirectory()) file = path.join(file,"index.html");
    fs.readFile(file,(e,data)=>{
      if(e){ res.writeHead(404,{"content-type":"text/plain; charset=utf-8"}); return res.end("Not found"); }
      res.writeHead(200,{"content-type":types[path.extname(file).toLowerCase()]||"application/octet-stream"});
      res.end(data);
    });
  });
}).listen(PORT,"0.0.0.0",()=>console.log("UNG-CAD listening on",PORT));
