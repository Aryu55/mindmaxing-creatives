import {mkdirSync,writeFileSync,cpSync,existsSync,rmSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {projects} from '../site/projects.mjs';
import {home,archive,project,about,page} from '../site/templates.mjs';
const output=resolve('dist');
// Only the generated output is replaced. No source/private directories are copied.
rmSync(output,{recursive:true,force:true});mkdirSync(output,{recursive:true});
const write=(path,content)=>{const full=resolve(output,path);mkdirSync(full.slice(0,full.lastIndexOf('/')),{recursive:true});writeFileSync(full,content);};
cpSync('site/assets',`${output}/assets`,{recursive:true});
cpSync('site/hero-preview.js',`${output}/assets/hero-preview.js`);
cpSync('site/studio.css',`${output}/assets/studio.css`);cpSync('site/studio.js',`${output}/assets/studio.js`);
if(existsSync('site/demos'))cpSync('site/demos',`${output}/demos`,{recursive:true});
// The isolated frames receive only visual tokens, generated from public records.
write('demos/theme.css', projects.map(p=>`html[data-project="${p.slug}"]{--project-accent:${p.accent}}`).join('\n'));
cpSync('favicon.png',`${output}/favicon.png`);
write('index.html',home());write('case-studies/index.html',archive());write('about/index.html',about());
for(const p of projects)write(`case-studies/${p.slug}/index.html`,project(p));
const legalPages = [
  { source: 'privacy', paths: ['privacy', 'privacy-policy'], title: 'Privacy policy', desc: 'Mindmaxing Studio privacy policy.' },
  { source: 'terms', paths: ['terms', 'terms-of-service', 'terms-and-conditions'], title: 'Terms of service', desc: 'Mindmaxing Studio terms of service.' }
];
for(const cfg of legalPages){
  if(existsSync(`${cfg.source}.html`)){
    const source=readFileSync(`${cfg.source}.html`,'utf8');
    const content=source.match(/<main[^>]*>([\s\S]*?)<\/main>/)?.[1]||'';
    for(const p of cfg.paths){
      const html=page({title:cfg.title,description:cfg.desc,path:`/${p}`,body:`<article class="shell legal-page">${content}</article>`});
      write(`${p}/index.html`,html);
      write(`${p}.html`,html);
    }
  }
}
write('case-studies.html',archive());write('about.html',about());
write('404.html',page({title:'Page not found',description:'Find your way back to Mindmaxing Studio.',path:'/404',body:'<section class="shell error-page"><span class="section-kicker">404 / A different path</span><h1>This page isn’t here.</h1><p>The work is still worth a look.</p><a class="button button-light" href="/case-studies">Explore the work ↗</a></section>'}));
write('_redirects','/index.html / 301\n/case-studies.html /case-studies 301\n/about.html /about 301\n/privacy-policy.html /privacy-policy 301\n/terms-of-service.html /terms-of-service 301\n/terms-and-conditions /terms-of-service 301\n');
write('_headers',`/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()\n/demos/*\n  Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors 'self'\n/assets/fonts/*\n  Access-Control-Allow-Origin: *\n  Cache-Control: public, max-age=31536000, immutable\n`);
write('sitemap.xml',`<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${['/','/case-studies','/about','/privacy','/privacy-policy','/terms','/terms-of-service',...projects.map(p=>'/case-studies/'+p.slug)].map(path=>`<url><loc>https://mindmaxing.one${path}</loc></url>`).join('')}</urlset>`);
// Outbound Radar Dashboard (partner telemetry)
if (existsSync('outbound/dashboard/index.html')) {
  mkdirSync(`${output}/radar`, {recursive: true});
  cpSync('outbound/dashboard/index.html', `${output}/radar/index.html`);
  cpSync('outbound/dashboard/index.html', `${output}/radar.html`);
  if (existsSync('outbound/dashboard/radar_data.json')) {
    cpSync('outbound/dashboard/radar_data.json', `${output}/radar/radar_data.json`);
    cpSync('outbound/dashboard/radar_data.json', `${output}/radar_data.json`);
  }
}
write('robots.txt','User-agent: *\nAllow: /\nDisallow: /demos/\nDisallow: /radar/\nDisallow: /radar\nSitemap: https://mindmaxing.one/sitemap.xml\n');
console.log(`Built ${projects.length} project pages + studio pages in ${output}`);

