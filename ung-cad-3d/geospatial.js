/* Georeferenced raster/image placement primitives (provider-neutral). */
(function(g){'use strict';
const R=6378137,rad=d=>d*Math.PI/180;
function webMercator(lat,lon){const cl=Math.max(-85.05112878,Math.min(85.05112878,+lat));return{x:R*rad(+lon),y:R*Math.log(Math.tan(Math.PI/4+rad(cl)/2)),crs:'EPSG:3857'}}
function localOffset(origin,point){const a=webMercator(origin.lat,origin.lon),b=webMercator(point.lat,point.lon);return{x:b.x-a.x,y:b.y-a.y}}
function imageLayer({url,bounds,crs='EPSG:4326',opacity=1,attribution=''}){if(!url||!bounds)throw new Error('url and bounds required');return{type:'georeferenced-image',url,bounds,crs,opacity:Math.max(0,Math.min(1,+opacity)),attribution}}
g.UNGCADGeo={webMercator,localOffset,imageLayer};})(window);