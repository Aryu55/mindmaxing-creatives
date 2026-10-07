import {createServer} from 'node:http';
import {readFileSync,existsSync,statSync} from 'node:fs';
import {resolve,extname,sep} from 'node:path';
const root=resolve('dist'),port=Number(process.env.PORT||3000);
const types={'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.woff2':'font/woff2','.webp':'image/webp','.jpg':'image/jpeg','.png':'image/png','.svg':'image/svg+xml','.xml':'application/xml','.txt':'text/plain'};
createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost');
  if(url.pathname==='/api/contact'){res.writeHead(503,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'This is the local preview. Email the studio directly, or use the production contact form.'}));return;}
  let path;try{path=resolve(root,'.'+decodeURIComponent(url.pathname));}catch{res.writeHead(400);res.end();return;}
  if(path!==root&&!path.startsWith(root+sep)){res.writeHead(403);res.end();return;}
  if(existsSync(path)&&statSync(path).isDirectory())path=resolve(path,'index.html');
  if(!existsSync(path)&&existsSync(path+'.html'))path+='.html';
  let status=200;if(!existsSync(path)){path=resolve(root,'404.html');status=404;}
  const headers={'Content-Type':types[extname(path)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Access-Control-Allow-Origin':'*','Cache-Control':'no-cache'};
  if(url.pathname.startsWith('/demos/'))headers['Content-Security-Policy']="default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'";
  res.writeHead(status,headers);res.end(readFileSync(path));
}).listen(port,'127.0.0.1',()=>console.log(`Mindmaxing preview: http://localhost:${port}`));
