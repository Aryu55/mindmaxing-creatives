const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
let toastTimer;
function notify(text) { const el=$('.toast'); if(!el)return; el.textContent=text; el.classList.add('visible'); clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),3000); }
const menu=$('.menu-toggle'), nav=$('#navigation');
function closeMenu(){if(!menu)return;menu.setAttribute('aria-expanded','false');nav.classList.remove('is-open');}
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('is-open',open);});
nav?.addEventListener('click',e=>{if(e.target.closest('a'))closeMenu();});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu?.getAttribute('aria-expanded')==='true'){closeMenu();menu.focus();}});

// Resolve older outreach links without requiring the archive to render first.
if(/^\/(?:index\.html|case-studies(?:\.html)?\/?)?$/.test(location.pathname)&&location.hash){
  let slug;try{slug=decodeURIComponent(location.hash.slice(1));}catch{slug='';}
  const known=($('meta[name=project-slugs]')?.content||'').split(',');
  if(known.includes(slug))location.replace(`/case-studies/${slug}`);
}

const search=$('#project-search'),filters=$$('[data-filter]'),leadBtns=$$('[data-filter-lead]'),leadActiveBar=$('#lead-active-bar'),leadActiveText=$('#lead-active-text'),leadClearBtn=$('#lead-clear-btn');
if(search){
  const rows=$$('.work-row');
  function apply(readURL=false){
    const params=new URLSearchParams(location.search);
    if(readURL)search.value=params.get('q')||'';
    let category=params.get('category')||'all';
    if(!filters.some(b=>b.dataset.filter===category))category='all';
    let lead=params.get('lead')||'';
    if(lead!=='aryan'&&lead!=='rahul')lead='';

    const query=search.value.trim().toLocaleLowerCase();let count=0;
    rows.forEach(row=>{
      const matchCat=(category==='all'||row.dataset.category===category);
      const matchLead=(!lead||row.dataset.lead===lead);
      const matchQuery=(!query||row.dataset.search.includes(query));
      const show=matchCat&&matchLead&&matchQuery;
      row.hidden=!show;
      if(show)count++;
    });
    filters.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===category)));
    leadBtns.forEach(b=>b.classList.toggle('is-active',b.dataset.filterLead===lead));
    $$('.authorship-card').forEach(c=>c.classList.toggle('is-active',c.dataset.leadCard===lead));
    if(leadActiveBar){
      if(lead){
        leadActiveBar.hidden=false;
        leadActiveText.textContent=`Showing ${lead==='aryan'?'Aryan Panchal’s (Technical)':'Rahul Saranya’s (Creative)'} work (${count} ${count===1?'project':'projects'})`;
      } else {
        leadActiveBar.hidden=true;
      }
    }
    $('#result-count').textContent=`${count} ${count===1?'project':'projects'}`;
    $('.empty-state').hidden=count!==0;
  }
  function setParams(p){const next=`${location.pathname}${p.size?'?'+p:''}`;history.replaceState(history.state,'',next);apply();}
  search.addEventListener('input',()=>{const p=new URLSearchParams(location.search);search.value.trim()?p.set('q',search.value.trim()):p.delete('q');setParams(p);});
  filters.forEach(b=>b.addEventListener('click',()=>{const p=new URLSearchParams(location.search);b.dataset.filter==='all'?p.delete('category'):p.set('category',b.dataset.filter);setParams(p);}));
  leadBtns.forEach(b=>b.addEventListener('click',()=>{
    const p=new URLSearchParams(location.search);
    const target=b.dataset.filterLead;
    if(p.get('lead')===target){p.delete('lead');}else{p.set('lead',target);p.delete('category');}
    setParams(p);
  }));
  leadClearBtn?.addEventListener('click',()=>{
    const p=new URLSearchParams(location.search);
    p.delete('lead');
    setParams(p);
  });
  $('[data-clear-filters]')?.addEventListener('click',()=>{search.value='';setParams(new URLSearchParams());search.focus();});
  window.addEventListener('popstate',()=>apply(true));apply(true);
  rows.forEach(a=>a.addEventListener('click',()=>{try{sessionStorage.setItem('mindmaxing-work-return',JSON.stringify({path:location.pathname+location.search,scroll:scrollY}));}catch{}}));
  try{const r=JSON.parse(sessionStorage.getItem('mindmaxing-work-return'));if(r?.path===location.pathname+location.search&&(performance.getEntriesByType('navigation')[0]?.type==='back_forward'||document.referrer.startsWith(location.origin+'/case-studies/')))requestAnimationFrame(()=>scrollTo(0,r.scroll));}catch{}
}
const back=$('[data-back-work]');
$$('[data-project-link]').forEach(link=>link.addEventListener('click',()=>{$$('img[data-media-kind]').forEach(img=>img.style.viewTransitionName='none');const image=$('img',link);if(image)image.style.viewTransitionName='project-'+link.getAttribute('href').split('/').pop();}));
if(back){try{const r=JSON.parse(sessionStorage.getItem('mindmaxing-work-return'));if(r&&/^\/case-studies(?:\?|$)/.test(r.path))back.href=r.path;}catch{}}
$('[data-copy-link]')?.addEventListener('click',async()=>{const canonical=$('link[rel=canonical]')?.href||location.href;try{await navigator.clipboard.writeText(canonical);notify('Project link copied');}catch{notify('Copy this project’s address from your browser.');}});

const form=$('#contact-form');
if(form){
  const context=new URLSearchParams(location.search).get('project')?.slice(0,120);
  if(context){form.elements.project.value=context;$('.project-context',form).textContent=`About a project like ${context}`;$('.project-context',form).hidden=false;}
  form.addEventListener('submit',async e=>{e.preventDefault();if(!form.reportValidity())return;const button=$('[type=submit]',form),status=$('.form-status',form);const values=Object.fromEntries(new FormData(form));button.disabled=true;status.textContent='Sending your brief…';status.dataset.state='pending';
    try{const response=await fetch('/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(values)});const body=await response.json();if(!response.ok||!body.success)throw new Error(body.error||'Your brief could not be sent. Please try again.');status.textContent='Your brief is with the studio. Thank you.';status.dataset.state='success';form.reset();if(context)form.elements.project.value=context;}catch(err){status.textContent=err.message||'Your brief could not be sent. You can email the studio directly.';status.dataset.state='error';}finally{button.disabled=false;}
  });
}

const shell=$('[data-demo-url]');
if(shell){
  const mount=$('.demo-mount',shell),cover=$('.demo-cover',shell),start=$('[data-demo-start]',shell),expand=$('[data-demo-expand]',shell),error=$('.demo-error',shell);
  let frame=null,timer,ready=false,expanded=false,priorFocus,previousOverflow='',inerted=[];
  const visibility = visible=>{frame?.contentWindow?.postMessage({channel:'mindmaxing-demo',type:'visibility',value:visible},'*');};
  function fail(){clearTimeout(timer);ready=false;delete shell.dataset.ready;frame?.remove();frame=null;cover.hidden=false;start.disabled=false;start.innerHTML='<span aria-hidden="true">▷</span> Start interactive demo';error.hidden=false;expand.hidden=true;if(expanded)closeExpanded();}
  function load(){if(frame)return;error.hidden=true;ready=false;start.disabled=true;start.textContent='Opening the interaction…';frame=document.createElement('iframe');frame.className='demo-frame is-loading';frame.title=`${$('.project-page').dataset.project} interactive reconstruction`;frame.setAttribute('sandbox','allow-scripts');frame.setAttribute('referrerpolicy','no-referrer');frame.setAttribute('aria-hidden','true');frame.tabIndex=-1;frame.src=shell.dataset.demoUrl;frame.addEventListener('error',fail,{once:true});mount.append(frame);timer=setTimeout(fail,12000);}
  start.addEventListener('click',load);$('[data-demo-retry]',shell).addEventListener('click',load);
  window.addEventListener('message',e=>{if(!frame||e.source!==frame.contentWindow||e.origin!=='null'||e.data?.channel!=='mindmaxing-demo')return;const {type,value}=e.data;
    if(type==='ready'){ready=true;clearTimeout(timer);cover.hidden=true;frame.classList.remove('is-loading');frame.removeAttribute('aria-hidden');frame.removeAttribute('tabindex');expand.hidden=false;shell.dataset.ready='true';visibility(!document.hidden);}
    else if(type==='height'&&Number.isFinite(value))frame.style.height=`${Math.max(280,Math.min(1500,value))}px`;
    else if(type==='close'&&expanded)closeExpanded();
  });
  // Keep the iframe in place when expanding: moving it would restart its document.
  function closeExpanded(){expanded=false;shell.classList.remove('is-expanded');shell.removeAttribute('role');shell.removeAttribute('aria-modal');shell.removeAttribute('aria-label');expand.textContent='Expand ⤢';document.body.style.overflow=previousOverflow;inerted.forEach(el=>{el.inert=false;});inerted=[];priorFocus?.focus();}
  expand.addEventListener('click',()=>{if(expanded){closeExpanded();return;}expanded=true;priorFocus=document.activeElement;previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';shell.classList.add('is-expanded');shell.setAttribute('role','dialog');shell.setAttribute('aria-modal','true');shell.setAttribute('aria-label','Expanded interactive demonstration');expand.textContent='Close ×';let current=shell;while(current.parentElement&&current!==document.body){for(const sibling of current.parentElement.children){if(sibling!==current&&!sibling.inert&&!['SCRIPT','STYLE'].includes(sibling.tagName)){sibling.inert=true;inerted.push(sibling);}}current=current.parentElement;}expand.focus();});
  document.addEventListener('keydown',e=>{if(!expanded)return;if(e.key==='Escape'){e.preventDefault();closeExpanded();}if(e.key==='Tab'){const focusables=[expand,frame];if(e.shiftKey&&document.activeElement===expand){e.preventDefault();frame.focus();}else if(!e.shiftKey&&document.activeElement===frame){e.preventDefault();expand.focus();}}});
  const observer=new IntersectionObserver(entries=>{if(ready)visibility(entries[0].isIntersecting&&!document.hidden);},{threshold:0});observer.observe(shell);
  document.addEventListener('visibilitychange',()=>{const r=shell.getBoundingClientRect();visibility(!document.hidden&&(expanded||(r.bottom>0&&r.top<innerHeight)));});
  window.addEventListener('pagehide',()=>visibility(false));
}
