#!/usr/bin/env node
// Local-only PhotoCraft CLI adapter. Never accepts shell command fragments.
'use strict';
const {spawnSync}=require('node:child_process');
const {existsSync,statSync,mkdirSync}=require('node:fs');
const path=require('node:path');
const ALLOWED=new Set(['.psd','.pcraft','.png','.jpg','.jpeg','.webp','.tif','.tiff']);
function execute(argv, options={}){
  const [action,input,output]=argv;
  if(!['info','convert'].includes(action)||!input||(action==='convert'&&!output)||(action==='info'&&output))throw Error('Usage: node bridge/photocraft-cli.js info <file> | convert <file> <output>');
  const source=path.resolve(input);
  if(!existsSync(source)||!statSync(source).isFile()||!ALLOWED.has(path.extname(source).toLowerCase()))throw Error('Input file missing or unsupported');
  const args=[action,source];
  if(action==='convert'){
    const dest=path.resolve(output);
    if(!ALLOWED.has(path.extname(dest).toLowerCase())||source===dest)throw Error('Output extension unsupported or same as input');
    mkdirSync(path.dirname(dest),{recursive:true});
    args.push(dest);
  }
  const binary=options.binary||process.env.PHOTOCRAFT_CLI||'photocraft-cli';
  const result=spawnSync(binary,args,{shell:false,encoding:'utf8',timeout:120000,maxBuffer:8*1024*1024});
  if(result.error)throw result.error;
  if(result.status!==0)throw Error((result.stderr||'PhotoCraft failed').slice(0,2000));
  return result.stdout;
}
if(require.main===module){try{process.stdout.write(execute(process.argv.slice(2)))}catch(e){console.error(e.message);process.exitCode=1}}
module.exports={execute};
