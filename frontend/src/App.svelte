<script>
  import { onMount } from 'svelte';
  import colors from '../colors.json';
  import charts from '../charts.json';
  import Input from '../components/Input.svelte'

  // populated by Flask backend
  let globals = $state({});
  let domains = $state({});
  let chart = $state(Object.keys(charts)[0]);
  let views = $state(["All Views"]);
  let view = $state("All Views");
  let inputs = $state({ "initial_time": 0, "final_time": 60 , "time_step": 0.0625});
  const unitsCache = new Map()

  let simulationResults = $state({});
  let errorMessage = $state("");
  let show_scenario_modal = $state(false);
  let scenario = $state('Baseline');
  let scenarios = $state({scenario: {'controls': {}, 'inputs': {}}});
  let kpiGroups = $state([])
  let activeKpiGroup = $state('Epidemiology');
  let isLoading = $state(false);
  let isInitializing = $state(true);
  
  let chartContainer;
  let kpiContainer;
  let Plotly;

  // $effect(() => {
  // })

  onMount(async () => {
    const mod = await import('plotly.js-dist-min');
    Plotly = mod.default;

    await fetchBaseline();
    await fetchGlobals();
    await fetchDomains();
    await setInputs();

    isInitializing = false;
  });

  async function fetchBaseline() {
    try {
      const response = await fetch('/api/baseline_parameters');
      const data = await response.json();
      if (response.ok) {
        scenarios['Baseline'] = {
          'controls': data.controls,
          'inputs': data.inputs
        };
      } else {
        errorMessage = "Failed to load model structural parameters.";
        isInitializing = false;
      }
    } catch (err) {
      errorMessage = "Could not parse baseline_parameters from Flask execution server.";
      isInitializing = false;
    }
  }

  async function fetchGlobals() {
    try {
     const response = await fetch('api/globals');
      const data = await response.json();
      if (response.ok) {
        globals = data.globals
        kpiGroups = data.kpi_groups
        await runSimulation();
      } else {
        errorMessage = "Failed to load model input globals.";
        isInitializing = false;
      }
    } catch (err) {
      errorMessage = "Could not parse input globals from Flask execution server.";
      isInitializing = false;
    }
  }

  async function fetchDomains() {
    try {
      const response = await fetch('api/domains');
      const data = await response.json();
      if (response.ok) {
        domains = data;
        views = views.concat(Object.keys(domains));
        //console.log('loaded domains',domains)
        await runSimulation();
      } else {
        errorMessage = "Failed to load model input domains.";
        isInitializing = false;
      }
    } catch (err) {
      errorMessage = "Could not parse input domains from Flask execution server.";
      isInitializing = false;
    }
  }
  
  async function runSimulation() {
    isLoading = true;
    errorMessage = "";

    let initialTime = inputs.initial_time;
    let finalTime = inputs.final_time;
    if (finalTime <= initialTime) {
      errorMessage = "Final time must be greater than initial time"
      finalTime = initialTime + 1
    }
        
    try {
      const response = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ initialTime, finalTime, timeStep:inputs.time_step, inputs })
      });

      const data = await response.json();

      if (response.ok) {
        simulationResults = data;
        renderChart();
        load_kpi_plots()
      } else {
        errorMessage = data.error || "Failed to process simulation data.";
      }
    } catch (err) {
      errorMessage = "Could not communicate with Flask backend API.";
    } finally {
      isLoading = false;
    }
  }

  async function setInputs() {
    Object.entries(globals).forEach(e => {
      inputs[e[0]] = e[1].default;
    });
    Object.entries(domains).forEach(d => {
      d[1].forEach(e => {
        inputs[e['py_name']] = e['default'];
      });
    });
  }

  function createScenario() {
    scenarios[scenario] = {
      'controls': {
        'initial_time': inputs['initial_time'],
        'final_time': inputs['final_time'],
        'time_step': inputs['time_step'],
      },
      'inputs': inputs,
    };
  }

  async function loadScenario() {
    inputs = scenarios[scenario]['inputs'];
    //console.log("loaded scenario",scenario,inputs);
    await runSimulation();
  }

  async function getUnits(pyName) {
    if (unitsCache.has(pyName)) return unitsCache.get(pyName) || ''
    const res = await fetch(`api/units?q=${pyName}`)
    const units = await res.text()
    unitsCache.set(pyName, units)
    return units
  }

  async function load_kpi_plots() {
    const response = await fetch(`/api/kpi_plots?q=${activeKpiGroup}`)
    const data = await response.json()
    if (response.ok) {
      Plotly.newPlot(kpiContainer,data.data,data.layout)
    } else {
      errorMessage = data.error || "Failed to process simulation data.";
    }
  }
  async function renderChart() {
    if (!Plotly || !simulationResults) return;

    const xData = simulationResults.time;
    const vars = simulationResults.variables;

    const colorScheme = colors.scheme;
    const chartValues = charts[chart]
    const targetTracks = chartValues.map((e, i) => ({key: e, name: e, color: colorScheme[i]}));

    // Filter and build traces only if keys exist in your model run data
    const traces = targetTracks
      .filter(track => vars[track.key] !== undefined)
      .map(track => ({
        x: xData,
        y: vars[track.key],
        type: 'scatter',
        mode: 'lines',
        name: track.name,
        line: { color: track.color, width: 2.5 }
      }));

    if (traces.length === 0) {
      errorMessage = "Warning: None of the target plotting variables were found in the model output keys. Check spelling.";
      return;
    }

    let yunits = getUnits(chartValues[0]); // no validation for *all* variables, blind trust
    const layout = {
      title: { text: chart, font: { size: 18 } },
      xaxis: { title: { text: 'Time (Days)' }, gridcolor: '#f0f0f0' },
      yaxis: { title: { text: yunits }, gridcolor: '#f0f0f0' },
      margin: { t: 50, b: 50, l: 60, r: 20 },
      hovermode: 'x unified', // Shows all variable tooltips at once on timeline drag
      plot_bgcolor: '#ffffff',
      paper_bgcolor: '#ffffff',
      legend: { x: 1, xanchor: 'right', y: -.5 }
    };

    const config = {
      responsive: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d']
    };

    Plotly.newPlot(chartContainer, traces, layout, config, { responsive: true });
  }

</script>

{#if errorMessage}
    <p class="error">{errorMessage}</p>
{/if}

<nav>
  <div class="brand">
    <span>LOGO</span>
    <span>TITLE</span>
  </div>
  <br>
  <div class="nav-options-wrapper">
    <button onclick={() => show_scenario_modal=true}>Scenario Testing</button>
    <button onclick={() => show_scenario_modal=true}>Sensitivity Testing</button>
  </div>
</nav>
{#if show_scenario_modal}
<div class="overlay"></div>
<div class="modal">
  <div class="modal-title">
    <span>Scenario Testing</span>
    <button class="close" onclick={() => show_scenario_modal=false}>close</button>
  </div>
  choose scenarios to compare
  remove, rename, import scenarios (validation)
  AI LLM analysis
</div>
{/if}
<main class="main">  
  <section class="globals">
    <div class="field">
      <label for="chart">Chart</label>
      <select name="chart" id="chart" bind:value={chart} onchange={renderChart}>
        {#each Object.keys(charts) as chart}
          <option value="{chart}">{chart}</option>
        {/each}
      </select>
    </div>
    <div class="field">
      <label for="view">View</label>
      <select name="view" id="view" bind:value={view}>
        {#each views as view_option}
          <option value="{view_option}">{view_option}</option>
        {/each}
      </select>
    </div>
    <div class="field">
      <label for="kpi-select">Key Performance Indicators</label>
      <select name="kpi-select" id="kpi-select" bind:value={activeKpiGroup} onchange={load_kpi_plots}>
        {#each kpiGroups as kpis_option}
          <option value="{kpis_option}">{kpis_option}</option>
        {/each}
      </select>
    </div>
    {#each Object.values(globals) as element}
      <div class="field">
        <label for="{element.py_name}">{element.real_name}</label>
        <input id="{element.py_name}" type="number" min="{element.min}" max="{element.max}" bind:value={inputs[element.py_name]} onchange={runSimulation} />
      </div>  
    {/each}
    <div class="field">
      <input type="text" name="" bind:value={scenario} list="select-scenario" placeholder="Select a scenario"/>
      <datalist id="select-scenario">
        {#each Object.keys(scenarios) as scenario}
          <option value="{scenario}">{scenario}</option>
        {/each}
      </datalist>
      <div class="scenario-buttons">
        <button onclick={createScenario}>Save scenario</button>
        <button onclick={loadScenario}>Load scenario</button>
      </div>
    </div>

  </section>

  <section class="displays">
    <section class="chart chart-wrapper" class:hidden={!simulationResults}>
      <div bind:this={chartContainer} class="plotly-target"></div>
    </section>
    <section bind:this={kpiContainer} class="kpi-wrapper">
    </section>
  </section>

  <section class="inputs">
    {#if view === "All Views"}
      <section class="input-group columns">
        {#each Object.entries(domains) as [domain, elements]}
          <div class="input-column column">
            <button class="domain-header" onclick={() => view=domain}>{domain}</button>
            {#each elements as element}
              <Input obj={element} bind:obj_of_inputs={inputs[element.py_name]} runSimulation={runSimulation}/>
            {/each}
          </div>
        {/each}
      </section>
    {:else}
      <section class="input-column column">
        <div class="input-header">
          <span>{view}</span>
          <button class="domain-header" onclick={() => view=views[0]}>[{views[0]} view]</button>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));">
          {#each Object.values(domains[view]) as element}
            <Input obj={element} bind:obj_of_inputs={inputs[element.py_name]} runSimulation={runSimulation}/>
          {/each}
        </div>
      </section>
    {/if}
  </section>
</main>

<style>
  main {
    background: white;
    font-size: 16px;
    color: #000;
  }
  select, input {
    background: none;
    color: #000;
    border: 2px solid #e2e8f0; 
  }
  .field { 
    display: flex; 
    flex-direction: row; 
    gap: 4px; 

    label {
      flex: 1;
      text-align: start;
      line-height: 1;
      font-size: .8rem;
    }
    select {
      height: min-content;
      width: 20ch;
      font-size: 14px;
    }
    input {
      height: min-content;
      width: 8ch;
      font-size: 14px;
    }
  }
  label { 
    font-size: 0.9rem; 
    color: #111; 
  }
  button { 
    background: none; 
    color: inherit;
    border: 2px solid #e2e8f0; 
    border-radius: 0; 
    cursor: pointer; 
    font-size: 1rem; 
    transition: background 0.2s; 
  }
  button:hover:not(:disabled) { 
    background: #efefef; 
  }
  button:disabled { 
    background: #94a3b8; 
    cursor: not-allowed; 
  }
  button.close {
    position: absolute;
    top: 12px;
    right: 12px;
  }

  .error { 
    color: #e22; 
    background: #fff; 
    padding: 12px; 
    font-weight: 500; 
  }

  nav {
    background: #fdfdfd;
    color: #000;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    padding: 12px;
    justify-content: space-between;
  }
  nav .brand {
    display: flex;
    gap: 24px;
  }
  nav .nav-options-wrapper {
    display: flex;
    justify-content: space-around;
    gap: 12px;
  }

  .overlay {
    background: #000a;
    width: 100vw;
    height: 100vh;
    position: fixed;
    left: 0;
    top: 0;
    z-index: 99;
  }
  .modal {
    background: #fff;
    border: 2px solid #e2e8f0;
    width: max(80vw, min-content);
    height: max(80vw, min-content);
    position: fixed;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    padding: 12px;
    z-index: 100;
  }
  .modal-title {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;

    span {
      font-weight: bold;
    }
  }

  .hidden { display: none; }

  .main {
    display: grid;
    grid-template-columns: 20% 80%;
    grid-template-areas: "globals displays" "inputs inputs";
    gap: 0;
    > * {
      background: white; 
      border: 1px solid #e2e8f0; 
    }
  }

  .globals {
    grid-area: globals;
    display: flex;
    flex-direction: column;
    padding: 12px;
    gap: 12px;
  }
  .field {
    display: flex;
    flex-direction: row;
    width: 100%;
    flex-wrap: wrap;
  }

  .displays {
    grid-area: displays;
    display: grid;
    grid-template-columns: 70% 30%;
  }
  .chart-wrapper { 
    border-radius: .5rem; 
    padding: 12px; 
    max-width: 100%;
  }
  .plotly-target { 
    max-width: 100%; 
    min-height: 450px; 
  }
  .kpi-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
    align-items: center;
    justify-content: center;
  }

  .inputs {
    grid-area: inputs;
    padding: 12px;
  }
  button.domain-header {
    background: none;
    border: none;
    padding: 0;
    font: inherit;
    cursor: pointer;
    text-align: inherit;
    &:hover {
      background: none;
      text-decoration: underline;
    }
  }
  .columns {
    display: flex;
    gap: 12px;
  }
  .column {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

</style>
