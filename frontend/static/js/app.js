(function(){
  "use strict";

  const summary = window.AQ_SUMMARY;
  const live = window.AQ_LIVE;
  let dailyChart = null;
  let hourlyChart = null;
  let liveFlowChart = null;
  let todayLiters = Number(live?.todayLiters || 0);

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

  function handleReading(data){
    const flow=Number(data.caudal_lpm || 0);
    const volume=Number(data.volumen_l || 0);
    const flowEl=document.getElementById('liveFlowValue');
    const todayEl=document.getElementById('todayLitersValue');

    if(flowEl) flowEl.textContent=`${flow.toFixed(2)} L/min`;
    todayLiters += volume;
    if(todayEl) todayEl.textContent=`${todayLiters.toFixed(2)} L`;
    addLivePoint(data.recorded_at || new Date(),flow);
  }

  function setupLiveStream(){
    if(!live?.streamUrl || typeof EventSource === 'undefined') return;
    const badge=document.getElementById('sseStatus');
    const source=new EventSource(live.streamUrl);

    source.onopen=()=>{if(badge) badge.textContent='En vivo';};
    source.onerror=()=>{if(badge) badge.textContent='Reconectando…';};
    source.onmessage=(event)=>{
      let data;
      try{data=JSON.parse(event.data);}catch(_err){return;}
      if(data.tipo==='lecturas') handleReading(data);
      if(data.tipo==='estado') setDeviceState(data.en_linea,data.valvula);
    };

    window.addEventListener('beforeunload',()=>source.close());
  }

  window.addEventListener('DOMContentLoaded',()=>{
    setupMenu();
    setupFilter();
    buildStaticCharts();
    buildLiveChart();
    setDeviceState(live?.sensorOnline,live?.valveState);
    setupLiveStream();
  });
})();
