(function(){
  "use strict";
  const summary = window.AQ_SUMMARY;

  function setupMenu(){
    const btn=document.querySelector('[data-menu-toggle]');
    const sidebar=document.getElementById('sidebar');
    if(btn && sidebar) btn.addEventListener('click',()=>sidebar.classList.toggle('open'));
  }

  function setupFilter(){
    const input=document.getElementById('tableFilter');
    const table=document.getElementById('historyTable');
    if(!input || !table) return;
    input.addEventListener('input',()=>{
      const q=input.value.trim().toLowerCase();
      table.querySelectorAll('tbody tr').forEach(row=>{
        row.hidden=q && !row.textContent.toLowerCase().includes(q);
      });
    });
  }

  function scaleCanvas(canvas){
    const dpr=window.devicePixelRatio||1, rect=canvas.getBoundingClientRect();
    canvas.width=Math.max(1,rect.width*dpr); canvas.height=Math.max(1,rect.height*dpr);
    const ctx=canvas.getContext('2d'); ctx.scale(dpr,dpr); return {ctx,w:rect.width,h:rect.height};
  }

  function lineChart(canvas, rows){
    if(!canvas || !rows?.length) return;
    const {ctx,w,h}=scaleCanvas(canvas), pad=42, values=rows.map(x=>Number(x.liters));
    const max=Math.max(...values,1)*1.12;
    ctx.clearRect(0,0,w,h); ctx.font='12px system-ui'; ctx.lineWidth=1;
    ctx.strokeStyle='#d8e8e5';
    for(let i=0;i<5;i++){const y=pad+(h-2*pad)*i/4;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(w-pad,y);ctx.stroke();}
    const x=i=>pad+(w-2*pad)*(values.length===1?0:i/(values.length-1));
    const y=v=>h-pad-(h-2*pad)*(v/max);
    ctx.beginPath();values.forEach((v,i)=>i?ctx.lineTo(x(i),y(v)):ctx.moveTo(x(i),y(v)));ctx.strokeStyle='#087f70';ctx.lineWidth=3;ctx.stroke();
    values.forEach((v,i)=>{ctx.beginPath();ctx.arc(x(i),y(v),4,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.strokeStyle='#087f70';ctx.lineWidth=2;ctx.stroke();});
    ctx.fillStyle='#607776';ctx.textAlign='center';rows.forEach((r,i)=>ctx.fillText(r.date.slice(5),x(i),h-13));ctx.textAlign='left';ctx.fillText(`${Math.round(max)} L`,4,pad+3);ctx.fillText('0 L',10,h-pad+3);
  }

  function barChart(canvas, rows){
    if(!canvas || !rows?.length) return;
    const {ctx,w,h}=scaleCanvas(canvas), pad=42, values=rows.map(x=>Number(x.liters)), max=Math.max(...values,1)*1.12;
    const cell=(w-2*pad)/rows.length, bw=Math.min(34,cell*.65);
    ctx.clearRect(0,0,w,h);ctx.font='11px system-ui';ctx.strokeStyle='#d8e8e5';
    for(let i=0;i<4;i++){const y=pad+(h-2*pad)*i/3;ctx.beginPath();ctx.moveTo(pad,y);ctx.lineTo(w-pad,y);ctx.stroke();}
    rows.forEach((r,i)=>{const x=pad+cell*(i+.5),bh=(h-2*pad)*(Number(r.liters)/max),top=h-pad-bh;ctx.fillStyle='#0aa792';roundRect(ctx,x-bw/2,top,bw,bh,7);ctx.fill();ctx.fillStyle='#607776';ctx.textAlign='center';ctx.fillText(r.hour,x,h-12);});
  }

  function roundRect(ctx,x,y,w,h,r){const rr=Math.min(r,w/2,h/2);ctx.beginPath();ctx.moveTo(x+rr,y);ctx.arcTo(x+w,y,x+w,y+h,rr);ctx.arcTo(x+w,y+h,x,y+h,rr);ctx.arcTo(x,y+h,x,y,rr);ctx.arcTo(x,y,x+w,y,rr);ctx.closePath();}
  function renderCharts(){if(!summary)return;lineChart(document.getElementById('dailyChart'),summary.daily);barChart(document.getElementById('hourlyChart'),summary.hourly);}
  window.addEventListener('DOMContentLoaded',()=>{setupMenu();setupFilter();renderCharts();});
  window.addEventListener('resize',()=>{clearTimeout(window.__aqResize);window.__aqResize=setTimeout(renderCharts,120);});
})();
