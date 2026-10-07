// Optional authoring tool. Production builds use the committed output assets.
const {chromium}=require('playwright');
const sharp=require('sharp');
const fs=require('node:fs');
const path=require('node:path');
const base=process.env.PREVIEW_URL||'http://localhost:3001';
(async()=>{
 const {projects}=await import('../site/projects.mjs');
 for(const dir of ['site/assets/previews','site/assets/social','site/review'])fs.mkdirSync(dir,{recursive:true});
 const browser=await chromium.launch({headless:true,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1280,height:889},deviceScaleFactor:1});
 for(const p of projects.filter(p=>!process.env.PROJECT_SLUG||p.slug===process.env.PROJECT_SLUG)){
  await page.goto(`${base}/demos/index.html?project=${p.slug}`,{waitUntil:'networkidle'});
  await page.locator('#experience h1').waitFor();await page.evaluate(()=>document.fonts.ready);
  const screenshot=await page.screenshot();
  await sharp(screenshot).webp({quality:85}).toFile(`site/assets/previews/${p.slug}.webp`);
  const original=`site/assets/projects/${p.slug}.webp`, source=fs.existsSync(original)?original:`site/assets/previews/${p.slug}.webp`;
  const image=(await sharp(source).resize(640,450,{fit:'cover',position:'top'}).jpeg({quality:85}).toBuffer()).toString('base64');
  await page.setViewportSize({width:1200,height:630});
  const esc=s=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  await page.setContent(`<html><head><style>@font-face{font-family:Instrument;src:url('${base}/assets/fonts/instrument-sans.woff2')}*{box-sizing:border-box}body{margin:0;background:#080a0d;color:#ecefed;font-family:Instrument,Arial;padding:52px;width:1200px;height:630px}.top{font-size:22px;letter-spacing:-1px;display:flex;justify-content:space-between;align-items:center}.top span{font-size:12px;color:#919ead;letter-spacing:0}.body{display:grid;grid-template-columns:420px 1fr;gap:35px;align-items:center;height:450px}.label{font-size:13px;color:#c5ad87;margin-bottom:20px}h1{font-size:56px;line-height:1.05;letter-spacing:-3px;margin:0 0 20px;font-weight:500}p{font-size:19px;line-height:1.5;color:#9eaab8}.image{border:1px solid #ffffff25;border-radius:9px;overflow:hidden;height:350px}img{width:100%;height:100%;object-fit:cover;object-position:top}.foot{font-size:12px;color:#8392a4}</style></head><body><div class="top">mindmaxing studio<span>Creative engineering · Mumbai</span></div><div class="body"><div><div class="label">Explore the project</div><h1>${esc(p.title)}</h1><p>${esc(p.summary)}</p></div><div class="image"><img src="data:image/jpeg;base64,${image}"></div></div><div class="foot">mindmaxing.one/case-studies/${p.slug} · Interactive reconstruction inside</div></body></html>`);
  await page.evaluate(()=>document.fonts.ready);
  await page.screenshot({path:`site/assets/social/${p.slug}.jpg`,type:'jpeg',quality:88});
  await page.setViewportSize({width:1280,height:889});console.log('Rendered',p.slug);
 }
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
