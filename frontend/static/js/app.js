(function(){
  "use strict";

  const summary = window.AQ_SUMMARY;
  const live = window.AQ_LIVE;
  let dailyChart = null;
  let hourlyChart = null;
  let liveFlowChart = null;
  let todayLiters = Number(live?.todayLiters || 0);
  let lastSeenReadingId = null;
  let lastReadingDate = null;
  let readingPollingInProgress = false;
  let readingPollingTimer = null;

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

  function buildStaticCharts(){
    if(!summary || typeof Chart === 'undefined') return;

    const dailyCanvas=document.getElementById('dailyChart');
    if(dailyCanvas && summary.daily?.length){
      dailyChart=new Chart(dailyCanvas,{
        type:'line',
        data:{
          labels:summary.daily.map(r=>r.date),
          datasets:[{
            label:'Litros/día',
            data:summary.daily.map(r=>Number(r.liters)),
            borderColor:'#087f70',
            backgroundColor:'rgba(8,127,112,.12)',
            fill:true,
            tension:.3
          }]
        },
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
      });
    }

    const hourlyCanvas=document.getElementById('hourlyChart');
    if(hourlyCanvas && summary.hourly?.length){
      hourlyChart=new Chart(hourlyCanvas,{
        type:'bar',
        data:{
          labels:summary.hourly.map(r=>r.hour),
          datasets:[{
            label:'Litros',
            data:summary.hourly.map(r=>Number(r.liters)),
            backgroundColor:'#0aa792',
            borderRadius:6
          }]
        },
        options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
      });
    }
  }

  function buildLiveChart(){
    const canvas=document.getElementById('liveFlowChart');
    if(!canvas || typeof Chart === 'undefined') return;

    liveFlowChart=new Chart(canvas,{
      type:'line',
      data:{labels:[],datasets:[{
        label:'Caudal (L/min)',
        data:[],
        borderColor:'#087f70',
        backgroundColor:'rgba(8,127,112,.10)',
        fill:true,
        tension:.25,
        pointRadius:2
      }]},
      options:{
        responsive:true,
        maintainAspectRatio:false,
        animation:false,
        plugins:{legend:{display:false}},
        scales:{y:{beginAtZero:true,title:{display:true,text:'L/min'}}}
      }
    });

    if(Number.isFinite(Number(live?.initialFlow))){
      addLivePoint(new Date(),Number(live.initialFlow));
    }
  }

  function addLivePoint(date,flow){
    if(!liveFlowChart) return;
    const label=new Date(date).toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit',second:'2-digit'});
    liveFlowChart.data.labels.push(label);
    liveFlowChart.data.datasets[0].data.push(Number(flow));
    while(liveFlowChart.data.labels.length>30){
      liveFlowChart.data.labels.shift();
      liveFlowChart.data.datasets[0].data.shift();
    }
    liveFlowChart.update('none');
  }

  function setDeviceState(online,valve){
    const status=document.getElementById('sensorStatus');
    const valveStatus=document.getElementById('valveStatus');
    if(status && online !== null && online !== undefined){
      status.textContent=online?'En línea':'Desconectado';
      status.classList.toggle('normal',Boolean(online));
      status.classList.toggle('warning',!online);
    }
    if(valveStatus && valve){
      valveStatus.textContent=`Válvula: ${valve}`;
    }
  }

  // SSE sigue escuchando cambios de estado de la válvula/dispositivo.
  // Las lecturas se dibujan por consulta HTTP para evitar depender de SSE.
  function setupLiveStream(){
    if(!live?.streamUrl || typeof EventSource === 'undefined') return;
    const source=new EventSource(live.streamUrl);
    source.onmessage=(event)=>{
      let data;
      try{data=JSON.parse(event.data);}catch(_err){return;}
      if(data.tipo==='estado') setDeviceState(data.en_linea,data.valvula);
    };
    window.addEventListener('beforeunload',()=>source.close());
  }

  // Consulta cada 3 segundos las lecturas persistidas por MQTT en PostgreSQL.
  // Usa el mismo endpoint /api/lecturas que ya se comprobó en producción.
  async function refreshLiveReadings(){
    if(readingPollingInProgress || !liveFlowChart) return;
    readingPollingInProgress=true;
    const badge=document.getElementById('sseStatus');
    try{
      const response=await fetch('/api/lecturas',{cache:'no-store'});
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      const result=await response.json();
      const readings=Array.isArray(result.readings)?result.readings:[];
      if(!readings.length){
        if(badge) badge.textContent='Sin lecturas';
        return;
      }

      const points=readings.slice(0,30).reverse();
      liveFlowChart.data.labels=points.map(r=>
        new Date(r.recorded_at).toLocaleTimeString('es-CO',{
          hour:'2-digit',minute:'2-digit',second:'2-digit'
        })
      );
      liveFlowChart.data.datasets[0].data=points.map(r=>Number(r.flow_l_min));
      liveFlowChart.update('none');

      const latest=points[points.length-1];

      // Mantiene actualizado el indicador de litros del día sin sumar
      // repetidamente las mismas lecturas en cada consulta.
      const ids=readings.map(r=>Number(r.id)).filter(Number.isFinite);
      const maxId=ids.length?Math.max(...ids):null;
      if(lastSeenReadingId === null){
        lastSeenReadingId=maxId;
        lastReadingDate=String(latest.recorded_at).slice(0,10);
      }else if(maxId !== null){
        const news=readings.filter(r=>Number(r.id)>lastSeenReadingId)
          .sort((a,b)=>Number(a.id)-Number(b.id));
        for(const r of news){
          const day=String(r.recorded_at).slice(0,10);
          if(day!==lastReadingDate){
            lastReadingDate=day;
            todayLiters=0;
          }
          todayLiters+=Number(r.volume_liters)||0;
        }
        if(news.length){
          const todayEl=document.getElementById('todayLitersValue');
          if(todayEl) todayEl.textContent=`${todayLiters.toFixed(2)} L`;
        }
        lastSeenReadingId=Math.max(lastSeenReadingId,maxId);
      }

      const flowEl=document.getElementById('liveFlowValue');
      if(flowEl) flowEl.textContent=`${Number(latest.flow_l_min).toFixed(2)} L/min`;
      if(badge) badge.textContent='Actualización cada 3 s';
    }catch(error){
      if(badge) badge.textContent='Reconectando…';
      console.error('[AquaHogar] Error consultando lecturas:',error);
    }finally{
      readingPollingInProgress=false;
    }
  }

  function setupReadingPolling(){
    if(!liveFlowChart) return;
    refreshLiveReadings();
    readingPollingTimer=window.setInterval(refreshLiveReadings,3000);
    window.addEventListener('beforeunload',()=>{
      window.clearInterval(readingPollingTimer);
    });
  }

  window.addEventListener('DOMContentLoaded',()=>{
    setupMenu();
    setupFilter();
    buildStaticCharts();
    buildLiveChart();
    setDeviceState(live?.sensorOnline,live?.valveState);
    setupLiveStream();
    setupReadingPolling();
  });
})();
