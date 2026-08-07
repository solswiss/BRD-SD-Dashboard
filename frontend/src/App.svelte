<script>
  import { onMount } from 'svelte';
  import colors from '../colors.json';
  import charts from '../charts.json';
  import Input from '../components/Input.svelte'

  // Constants
  const SCENARIO_BASELINE = 'Baseline';
  const DEFAULT_TIME_STEP = 0.0625;
  const COLOR_SCHEME = colors.scheme;
  const LINE_TYPES = ['solid', 'dashdot', 'dot'];

  // State
  let globals = $state({});
  let domains = $state({});
  let chart = $state(Object.keys(charts)[0]);
  let views = $state(["All Views"]);
  let view = $state("All Views");
  
  let inputs = $state({ 
    initial_time: 0, 
    final_time: 60, 
    time_step: DEFAULT_TIME_STEP 
  });
  let simulationResults = $state({});
  let errorMessage = $state("");
  let showScenarioModal = $state(false);
  let inputScenarioName = $state('10A');
  let ephScenario = $state(SCENARIO_BASELINE);
  
  let scenarios = { [SCENARIO_BASELINE]: { 'controls': {}, 'inputs': {} } };
  let scenario = $state(SCENARIO_BASELINE);
  let selectedScenarios = $state([SCENARIO_BASELINE]);
  let kpiGroups = $state([]);
  let activeKpiGroup = $state('Epidemiology');
  let isLoading = $state(false);
  let isInitializing = $state(true);
  
  let chartContainer;
  let kpiContainer;
  let Plotly;

  const unitsCache = new Map();
  const fetchCache = new Map();

  // Sync inputs to current scenario
  $effect(() => {
    const snapshot = $state.snapshot(inputs);
    scenarios[scenario]['inputs'] = snapshot;
    if (selectedScenarios.length === 0) selectedScenarios = [SCENARIO_BASELINE];
  });

  onMount(async () => {
    const mod = await import('plotly.js-dist-min');
    Plotly = mod.default;

    await Promise.all([fetchBaseline(), fetchGlobals(), fetchDomains()]);
    await setInputs();
    await runSimulation();

    isInitializing = false;
  });

  async function fetchWithCache(url) {
    if (fetchCache.has(url)) return fetchCache.get(url);
    try {
      const response = await fetch(url);
      const data = await response.json();
      if (response.ok) {
        fetchCache.set(url, data);
        return data;
      } else {
        throw new Error(`API error: ${response.status}`);
      }
    } catch (err) {
      errorMessage = `Failed to fetch from ${url}`;
      isInitializing = false;
      throw err;
    }
  }

  async function fetchBaseline() {
    try {
      const data = await fetchWithCache('/api/baseline_parameters');
      scenarios[SCENARIO_BASELINE] = {
        'controls': data.controls,
        'inputs': data.inputs
      };
    } catch (err) {
      errorMessage = "Could not load baseline parameters.";
      isInitializing = false;
    }
  }

  async function fetchGlobals() {
    try {
      const data = await fetchWithCache('/api/globals');
      globals = data.globals;
      kpiGroups = data.kpi_groups;
    } catch (err) {
      errorMessage = "Could not load input globals.";
      isInitializing = false;
    }
  }

  async function fetchDomains() {
    try {
      const data = await fetchWithCache('/api/domains');
      domains = data;
      views = ["All Views", ...Object.keys(domains)];
    } catch (err) {
      errorMessage = "Could not load input domains.";
      isInitializing = false;
    }
  }

  function updateInputValue(event=null) {
    if (event) console.log('updateinputvalue called by',event.currentTarget)
    console.log('running',scenario,inputs['vaccination_coverage'])
    console.log(scenarios[scenario]['inputs']['vaccination_coverage'])
    scenarios[scenario]['inputs'] = inputs
    console.log(scenarios[scenario]['inputs']['vaccination_coverage'])
    runSimulation()
  }

  async function runSimulation() {
    isLoading = true;
    errorMessage = "";

    let finalTime = inputs.final_time;
    const initialTime = inputs.initial_time;
    
    if (finalTime <= initialTime) {
      finalTime = initialTime + 1;
    }
    const inputsDraft = Object.fromEntries(
      Object.entries(scenarios).map(([k, v]) => [k, v.inputs])
    );
    
    try {
      const response = await fetch('/api/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          initialTime, 
          finalTime, 
          timeStep: inputs.time_step, 
          inputs: inputsDraft 
        })
      });

      const data = await response.json();

      if (response.ok) {
        simulationResults = data
        //console.log(simulationResults[SCENARIO_BASELINE]['variables']['init s'][0])
        //console.log(simulationResults[SCENARIO_BASELINE]['variables']['initial population'][0])
        renderChart()
        loadKpiPlots()
      } else {
        errorMessage = data.error || "Simulation failed.";
      }
    } catch (err) {
      errorMessage = "Could not communicate with backend.";
      console.error(err);
    } finally {
      isLoading = false;
    }
  }

  async function setInputs() {
    Object.entries(globals).forEach(([key, val]) => {
      inputs[key] = val.default;
    });
    Object.entries(domains).forEach(([_, elements]) => {
      elements.forEach((el) => {
        inputs[el.py_name] = el.default;
      });
    });
  }

  async function createScenario() {
    const snapshot = $state.snapshot(inputs);
    scenarios[ephScenario] = {
      'controls': {
        'initial_time': inputs.initial_time,
        'final_time': inputs.final_time,
        'time_step': inputs.time_step,
      },
      'inputs': snapshot,
    };
    scenario = ephScenario;
    //if (Object.keys(selectedScenarios).length === 1 && Object.keys(selectedScenarios)[0] === SCENARIO_BASELINE) selectedScenarios.push(scenario)
    selectedScenarios.push(scenario)
    console.log('created',scenario)
    renderChart()
    await runSimulation()
  }

  async function loadScenario() {
    scenario = ephScenario
    inputs = scenarios[scenario]['inputs']
    console.log('loaded',scenario)
    await runSimulation();
  }

  async function deleteScenario() {
    if (ephScenario === SCENARIO_BASELINE) {
      errorMessage = "Cannot delete the Baseline scenario.";
      return;
    }
    
    delete scenarios[ephScenario];
    
    if (scenario === ephScenario) {
      scenario = SCENARIO_BASELINE;
      ephScenario = scenario;
      inputs = scenarios[scenario]['inputs'];
      await runSimulation();
    }
  }

  async function importScenario(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      scenarios[inputScenarioName] = {
        'controls': {
          'initial_time': inputs.initial_time,
          'final_time': inputs.final_time,
          'time_step': inputs.time_step,
        },
        'inputs': data,
      };
      scenario = inputScenarioName;
      ephScenario = scenario;
      console.log('imported',scenario)
      await runSimulation();
    } catch {
      errorMessage = "Failed to import scenario.";
    }
  }

  function exportScenario() {
    const blob = new Blob([JSON.stringify(inputs, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${scenario}_params.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  async function getUnits(pyName) {
    if (unitsCache.has(pyName)) return unitsCache.get(pyName) || '';
    
    try {
      const res = await fetch(`/api/units?q=${pyName}`);
      const units = await res.text();
      unitsCache.set(pyName, units);
      return units;
    } catch {
      return '';
    }
  }

  async function loadKpiPlots() {
    try {
      const response = await fetch(`/api/kpi_plots?q=${activeKpiGroup}`);
      const data = await response.json();
      
      if (response.ok) {
        Plotly.newPlot(kpiContainer, data.data, data.layout);
      } else {
        errorMessage = "Failed to load KPI plots.";
      }
    } catch (err) {
      console.error(err);
    }
  }

  function buildTrace(key, xData, vars, targetTracks, colors, lineType) {
    // Filter and build traces only if keys exist in your model run data
    try {
      return targetTracks
      .filter(track => vars[track.key] !== undefined)
      .map((track, i) => ({
        x: xData,
        y: vars[track.key],
        type: 'scatter',
        mode: 'lines',
        name: `${key}: ${track.name}`,
        line: { dash: lineType, color: track.color, width: 2.5 },
        legendgroup: SCENARIO_BASELINE,
        showlegend: false,
        marker: { color: colors ? colors[i] : null }
      }))
    } catch (err) {
      console.error(`While building a trace for ${key}:`,err)
    }
  }

  async function renderChart(event=null) {
    console.log('rendering',chart,scenario,inputs['vaccination_coverage'])
    //if (event) console.log('called by',event.currentTarget)
    if (!Plotly || (Object.keys(Object.values(simulationResults[selectedScenarios[0]])[1] || {})).length === 0) {
      console.log('buffering; exiting early')
      return
    }
    const chartValues = charts[chart]
    const targetTracks = chartValues.map((e) => ({key: e, name: e}));
    let colorScheme = colors.scheme
    const tracksLength = targetTracks.length
    const colorsOverflow = (colorScheme.length / tracksLength) >= Object.keys(scenarios).length
    const colorsUnderflow = colorScheme.length < tracksLength
    let traces = []
    let lineTypes = ['solid', 'dashdot', 'dot']
    for (const [i,k] of Object.keys(scenarios).filter(k => selectedScenarios.includes(k)).entries()) {
      if (!simulationResults[k]) continue;
      if (colorsUnderflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, lineTypes[i%tracksLength]))
      else if (colorsOverflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, colorScheme.slice(i*tracksLength, tracksLength), lineTypes[i%tracksLength]))
      else traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, colorScheme, lineTypes[i%tracksLength]))
    }
    if (traces.length === 0) {
      errorMessage = "Warning: None of the target plotting variables were found in the model output keys. Check spelling.";
      return;
    }

    let yunits = await getUnits(chartValues[0]); // no validation for *all* variables, blind trust
    const layout = {
      title: { text: chart, font: { size: 18 } },
      xaxis: { title: { text: 'Time (Days)' }, gridcolor: '#f0f0f0' },
      yaxis: { title: { text: yunits }, gridcolor: '#f0f0f0' },
      margin: { t: 50, b: 50, l: 60, r: 20 },
      hovermode: 'x unified', // Shows all variable tooltips at once on timeline drag
      plot_bgcolor: '#ffffff',
      paper_bgcolor: '#ffffff',
      legend: { orientation:'h', yanchor:'top', y:-0.2, 'xanchor':'left', x:0 }
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
    <button onclick={() => showScenarioModal=true}>Scenario Testing</button>
    <button onclick={() => showScenarioModal=true}>Sensitivity Testing</button>
  </div>
</nav>
{#if showScenarioModal}
<div class="overlay"></div>
<div class="modal">
  <div class="modal-title">
    <span>Scenario Testing</span>
    <button class="close" onclick={() => showScenarioModal=false}>close</button>
  </div>
  <label for="scenario-testing-select">Choose scenarios to compare (hold Ctrl/Cmd)</label>
  <select id="scenario-testing-select" onchange={renderChart} multiple bind:value={selectedScenarios}>
    {#each Object.keys(scenarios) as s}
      <option value={s}>{s}</option>
    {/each}
  </select>
  todo: AI LLM analysis
  <div>
    <input type="file" accept=".json">
    <input class="input-scenario" type="text" bind:value={inputScenarioName}>
    <button onclick={importScenario}>Import</button>
  </div>
</div>
{/if}

<main class="main">
  <section class="globals">
    <div class="field">
      <label for="chart">Chart</label>
      <select name="chart" id="chart" bind:value={chart} onchange={renderChart}>
        {#each Object.keys(charts) as chartOption}
          <option value="{chartOption}">{chartOption}</option>
        {/each}
      </select>
    </div>
    <div class="field">
      <label for="view">View</label>
      <select name="view" id="view" bind:value={view}>
        {#each views as viewOption}
          <option value="{viewOption}">{viewOption}</option>
        {/each}
      </select>
    </div>
    <div class="field">
      <label for="kpi-select">KPI</label>
      <select name="kpi-select" id="kpi-select" bind:value={activeKpiGroup} onchange={loadKpiPlots}>
        {#each kpiGroups as kpiOption}
          <option value="{kpiOption}">{kpiOption}</option>
        {/each}
      </select>
    </div>
    {#each Object.values(globals) as element}
      <div class="field">
        <label for="{element.py_name}">{element.real_name}</label>
        <input 
          id="{element.py_name}" 
          type="number" 
          min="{element.min}" 
          max="{element.max}" 
          bind:value={inputs[element.py_name]} 
          onchange={runSimulation} 
        />
      </div>
    {/each}
    <div class="field">
      <div class="scenario-buttons">
        <button onclick={createScenario}>Save as</button>
        <button onclick={loadScenario}>Load</button>
        <button onclick={exportScenario}>Export</button>
        <button onclick={deleteScenario}>Delete</button>
      </div>
      <input 
        class="input-scenario" 
        type="text" 
        bind:value={ephScenario} 
        list="select-scenario" 
        placeholder="Select a scenario"
      />
      <datalist id="select-scenario">
        {#each Object.keys(scenarios) as scenarioOption}
          <option value="{scenarioOption}">{scenarioOption}</option>
        {/each}
      </datalist>
      <span class="italics detail-text">Working: {scenario}</span>
    </div>
  </section>

  <section class="displays">
    <section class="chart chart-wrapper" class:hidden={!simulationResults}>
      <div bind:this={chartContainer} class="plotly-target"></div>
    </section>
    <section bind:this={kpiContainer} class="kpi-wrapper"></section>
  </section>

  <section class="inputs">
    {#if view === "All Views"}
      <section class="input-group columns">
        {#each Object.entries(domains) as [domainName, elements]}
          <div class="input-column column">
            <button class="domain-header" onclick={() => view = domainName}>{domainName}</button>
            {#each elements as element}
              <Input 
                obj={element} 
                bind:obj_of_inputs={inputs[element.py_name]} 
                default_value={scenarios[SCENARIO_BASELINE]['inputs'][element.py_name]} 
                func={updateInputValue}
              />
            {/each}
          </div>
        {/each}
      </section>
    {:else}
      <section class="input-column column">
        <div class="input-header">
          <span>{view}</span>
          <button class="domain-header" onclick={() => view = "All Views"}>[All Views]</button>
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));">
          {#each Object.values(domains[view]) as element}
            <Input 
              obj={element} 
              bind:obj_of_inputs={inputs[element.py_name]} 
              default_value={scenarios[SCENARIO_BASELINE]['inputs'][element.py_name]} 
              func={updateInputValue}
              />
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
    select, .input-scenario {
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
    font-size: .8rem;
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

  .italics {
    font-style: italic;
  }
  .detail-text {
    font-size: .6rem;
    color: #333;
    line-height: 1;
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