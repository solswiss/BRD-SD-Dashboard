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
  const SENSITIVITY_MODES = ['parametric', 'heatmap'];
  const MIN_STEP_VALUE = 0.1;
  const MAX_COMBINATIONS = 2500;

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
  let showSensitivityModal = $state(false);
  let inputScenarioName = $state('10A');
  let ephScenario = $state(SCENARIO_BASELINE);
  
  let scenarios = { [SCENARIO_BASELINE]: { 'controls': {}, 'inputs': {} } };
  let scenario = $state(SCENARIO_BASELINE);
  let selectedScenarios = $state([SCENARIO_BASELINE]);
  let kpiGroups = $state(['']);
  let activeKpiGroup = $state('');
  let isLoading = $state(false);
  let isInitializing = $state(true);
  
  let sensitivityChartContainer
  let sensitivityChartContainer1
  let chartContainer;
  let kpiContainer;
  let Plotly;

  const unitsCache = new Map();
  const fetchCache = new Map();

  // Sensitivity testing state
  let sensitivityChartWidth = $state(0)
  let statefulVariables = $state({})
  let constantVariables = $state({})
  let sensitivityMode = $state('parametric');
  let sensitivityYVariable = $state(null);
  let sensitivityXVariable = $state('time');
  let sensitivityZVariable = $state(null)
  let sensitivityXRange = $state({ min: null, max: null });
  let sensitivityYRange = $state({ min: null, max: null });
  let sensitivityStep = $state(2);
  let sensitivityResults = $state(null);
  let sensitivityStatus = $state('idle'); // idle, running, done
  let sensitivityError = $state('');

  // Sync inputs to current scenario
  $effect(() => {
    const snapshot = $state.snapshot(inputs);
    scenarios[scenario]['inputs'] = snapshot;
    //console.log(scenarios[SCENARIO_BASELINE]['inputs']['vaccination_coverage'])
    if (selectedScenarios.length === 0) selectedScenarios = [SCENARIO_BASELINE];
    
    if (showSensitivityModal) {
      if (sensitivityXVariable !== 'time') {
        const sensX = constantVariables[sensitivityXVariable]
        sensitivityXRange.min = sensX.min
        sensitivityXRange.max = sensX.max
      }
      if (sensitivityYVariable && sensitivityMode === 'heatmap') {
        try {
          const sensY = constantVariables[sensitivityYVariable]
          sensitivityYRange.min = sensY.min
          sensitivityYRange.max = sensY.max
        } catch (err) {
          console.log(err)
        }
      }
    }
  });

  onMount(async () => {
    const mod = await import('plotly.js-dist-min');
    Plotly = mod.default;

    await Promise.all([fetchMetadata(), fetchBaseline(), fetchGlobals(), fetchDomains()]);
    await setInputs();
    await runSimulation();
    
    isInitializing = false;
  });

  async function fetchMetadata() {
    try {
      const data = await fetchWithCache('/api/metadata')
      statefulVariables = {...data.statefuls}
      constantVariables = {...data.constants}
    } catch (err) {
      errorMessage = "Could not load metadata.";
      isInitializing = false;
    }
  }

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
      activeKpiGroup = kpiGroups[0]
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

  async function runSimulation() {
    console.log('running')
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

      const data = await response.json()

      if (response.ok) {
        simulationResults = data;
        renderChart();
        loadKpiPlots();
      } else {
        errorMessage = data.error || "Simulation failed.";
        console.log('err')
      }
    } catch (err) {
      errorMessage = "Could not communicate with backend.";
      console.error(err)
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
    selectedScenarios.push(scenario)
    await runSimulation();
  }

  async function loadScenario() {
    inputs = scenarios[scenario]['inputs'];
    selectedScenarios.push(scenario)
    await runSimulation()
  }

  async function deleteScenario() {
    if (ephScenario === SCENARIO_BASELINE) {
      errorMessage = "Cannot delete the Baseline scenario.";
      return;
    }
    
    delete scenarios[ephScenario];
    selectedScenarios.splice(selectedScenarios.indexOf(ephScenario),1)
    
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

  function getRealName(pyName) {
    const constCheck = constantVariables[pyName]
    if (constCheck) return constCheck.real_name
    const stateCheck = statefulVariables[pyName]
    if (stateCheck) return stateCheck.real_name
    //const auxCheck = 
    return pyName.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ")
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

  async function renderChart() {
    if (!Plotly || Object.keys(simulationResults[SCENARIO_BASELINE] || {}).length === 0) return;
    console.log('rendering')
    const chartValues = charts[chart]
    const targetTracks = chartValues.map((e) => ({key: e, name: e}));
    const tracksLength = targetTracks.length
    const colorsOverflow = (COLOR_SCHEME.length / tracksLength) >= Object.keys(scenarios).length
    const colorsUnderflow = COLOR_SCHEME.length < tracksLength
    let traces = []
    for (const [i,k] of Object.keys(scenarios).filter(k => selectedScenarios.includes(k)).entries()) {
      if (!simulationResults[k]) continue;
      if (colorsUnderflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, LINE_TYPES[i%tracksLength]))
      else if (colorsOverflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, COLOR_SCHEME.slice(i*tracksLength, tracksLength), LINE_TYPES[i%tracksLength]))
      else traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, COLOR_SCHEME, LINE_TYPES[i%tracksLength]))
    }
    if (traces.length === 0) {
      errorMessage = "Warning: None of the target plotting variables were found in the model output keys. Check spelling.";
      return;
    }

    let yunits = await getUnits(chartValues[0]);
    const layout = {
      title: { text: chart, font: { size: 18 } },
      xaxis: { title: { text: 'Time (Days)' }, gridcolor: '#f0f0f0' },
      yaxis: { title: { text: yunits }, gridcolor: '#f0f0f0' },
      margin: { t: 50, b: 50, l: 60, r: 20 },
      hovermode: 'x unified',
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

  // ============ SENSITIVITY TESTING FUNCTIONS ============

  // Update sensitivity mode and reset variable selections
  function updateSensitivityMode() {
    sensitivityError = '';
    sensitivityXVariable = 'time';
    sensitivityYVariable = null
    if (Plotly) {
      Plotly.purge(sensitivityChartContainer)
      Plotly.purge(sensitivityChartContainer1)
    }
  }

  // Validate range and apply 5% minimum step floor
  function validateAndNormalizeRange(min, max, variableName) {
    if (min === null || max === null) {
      sensitivityError = `${variableName} requires both min and max values`;
      return null;
    }
    
    if (min >= max) {
      sensitivityError = `${variableName} min must be less than max`;
      return null;
    }

    const range = max - min;
    const maxStep = getMaximumStep(range)
    if (sensitivityStep > maxStep) {
      sensitivityStep = maxStep
    }

    return { min, max, range };
  }

  // Calculate steps based on precision level
  function getStepCount() {
    if (sensitivityStep <= 0) {
      throw Error('Sensitivity step must be greater than zero.')
    }
    return sensitivityStep
  }

  // Validate total combinations don't exceed limit
  function validateTotalCombinations(xSteps, ySteps = 1) {
    const total = xSteps * ySteps;
    if (total > MAX_COMBINATIONS) {
      sensitivityError = `Total combinations (${total}) exceeds limit (${MAX_COMBINATIONS}). Reduce precision.`;
      return false;
    }
    return true;
  }

  // Calculate maximum step size for a given range
  function getMaximumStep(range) {
    return (range.max - range.min) / MIN_STEP_VALUE;
  }

  // Build parameter grid for backend
  function buildParameterGrid() {
    const steps = getStepCount();
    
    let xRange, yRange;
    let xVarName, yVarName;

    // Validate Y variable (required for all modes)
    if (!sensitivityYVariable) {
      sensitivityError = 'Y-axis/dependent variable is required';
      return null;
    }

    yVarName = sensitivityYVariable;

    if (sensitivityMode === 'heatmap') {
      yVarName = sensitivityYVariable;
      yRange = validateAndNormalizeRange(
        sensitivityYRange.min,
        sensitivityYRange.max,
        yVarName
      );
      if (!yRange) return null;

      if (!validateTotalCombinations(steps, steps)) return null;

      return {
        mode: 'heatmap',
        variables: {
          [yVarName]: {
            min: yRange.min,
            max: yRange.max,
            steps: steps
          },
          [sensitivityXVariable || 'time']: {
            min: sensitivityXRange.min,
            max: sensitivityXRange.max,
            steps: steps
          },
          [sensitivityZVariable]: null
        }
      };
    } else {
      // Parametric: sweep only X (or time if X is not specified)
      xVarName = sensitivityXVariable || 'time';
      
      if (xVarName !== 'time') {
        xRange = validateAndNormalizeRange(
          sensitivityXRange.min,
          sensitivityXRange.max,
          xVarName
        );
        if (!xRange) return null;
      }

      if (!validateTotalCombinations(steps)) return null;

      const varDef = xVarName === 'time' 
        ? { min: inputs.initial_time, max: inputs.final_time, steps: steps }
        : { min: xRange.min, max: xRange.max, steps: steps };

      return {
        mode: 'parametric',
        variables: {
          [xVarName]: varDef,
          [yVarName]: null
        }
      };
    }
  }

  // Send sensitivity request to backend
  async function runSensitivityAnalysis() {
    sensitivityError = '';
    sensitivityStatus = 'running';

    const paramGrid = buildParameterGrid();
    if (!paramGrid) {
      sensitivityStatus = 'idle';
      return;
    }

    try {
      const response = await fetch('/api/sensitivity', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...paramGrid,
          scenario: scenario,
          baseInputs: scenarios[scenario]['inputs']
        })
      });

      const data = await response.json();

      if (response.ok) {
        sensitivityResults = data;
        sensitivityStatus = 'done';
        renderSensitivityChart();
      } else {
        sensitivityError = data.error || 'Sensitivity analysis failed';
        sensitivityStatus = 'idle';
      }
    } catch (err) {
      sensitivityError = 'Could not communicate with backend';
      console.error(err);
      sensitivityStatus = 'idle';
    }
  }

  // Render sensitivity results based on mode
  function renderSensitivityChart() {
    if (!sensitivityResults || !Plotly) return;

    if (sensitivityMode === 'heatmap') {
      renderSensitivityHeatmap();
    } else {
      renderSensitivityParametric();
    }
  }

  function renderSensitivitySummary(values, xVar, yVar, margin) {
    // Build summary curve (final Y vs X parameter)
    console.log('values',values)
    const summaryTrace = {
      x: values.map(r => r.x_param_value),
      y: values.map(r => r.y_final_value),
      type: 'scatter',
      mode: 'lines+markers',
      name: `${yVar} vs ${xVar}`,
      line: { color: '#000', width: 3 },
      marker: { size: 8 },
    };

    const realX = getRealName(xVar)
    const realY = getRealName(yVar)
    const layout = {
      hovermode: 'closest',
      title: {text:`${realX} vs ${realY}`},
      xaxis: { title: {text: realX }},
      yaxis: { title: {text: realY }},
      width: sensitivityChartWidth,
      margin: { l: margin, r: margin, t: margin, b: margin, } 
    };
    const config = {
      responsive: false,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d']
    };
    Plotly.newPlot(sensitivityChartContainer1, [summaryTrace], layout, config
    );
  }

  // Render parametric sensitivity: N time-series curves + 1 summary curve
  function renderSensitivityParametric() {
    const xVar = sensitivityXVariable;
    const yVar = sensitivityYVariable;

    // Build N traces (one per X parameter value, showing Y vs time)
    const timeSeriesTraces = sensitivityResults.time_series.map((series, idx) => ({
      x: series.time,
      y: series.y_values,
      type: 'scatter',
      mode: 'lines',
      name: `${series.x_param_value.toFixed(2)}`,
      line: { color: COLOR_SCHEME[idx % COLOR_SCHEME.length], width: 1.5 },
      //xaxis: 'Time (days)',
      //yaxis: yVar,
    }));

    const realY = getRealName(sensitivityResults.y_variable)
    let margin = 50
    const layout = {
      hovermode: 'closest',
      title: {text:`Sensitivity — ${realY}`},
      xaxis: { title: {text:'Time'}},
      yaxis: { title: {text: realY }},
      width: sensitivityChartWidth,
      margin: { l: margin, r: margin, t: margin, b: margin, } 
    };
    
    const config = {
      responsive: false,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d']
    };

    Plotly.newPlot(sensitivityChartContainer, timeSeriesTraces, layout, config
    );
    
    renderSensitivitySummary(sensitivityResults.final_values, xVar, yVar, margin)
  }

  // Render heatmap sensitivity plot
  function renderSensitivityHeatmap() {
    let trace = {
      z: sensitivityResults.grid.z_values,
      x: sensitivityResults.grid.x_values,
      y: sensitivityResults.grid.y_values,
      type: 'heatmap',
      colorscale: 'Viridis'
    }
    if (sensitivityStep <= 10) {
      trace = {
        z: sensitivityResults.grid.z_values,
        x: sensitivityResults.grid.x_values,
        y: sensitivityResults.grid.y_values,
        text: sensitivityResults.z_values_rounded,
        texttemplate: '%{text}',
        type: 'heatmap',
        colorscale: 'Viridis'
      }
    }

    let margin = 30
    const realX = getRealName(sensitivityResults.x_variable)
    const realY = getRealName(sensitivityResults.y_variable)
    const layout = {
      title: {text:`${realX} and ${realY}`},
      xaxis: { title: {text: realX }},
      yaxis: { title: {text: realY }},
      width: sensitivityChartWidth,
      margin: { l: margin, r: margin, t: margin, b: margin, } 
    };

    const config = {
      responsive: false,
      displaylogo: false,
      modeBarButtonsToRemove: ['select2d', 'lasso2d']
    };
    Plotly.newPlot(sensitivityChartContainer, [trace], layout, config);
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
    <button onclick={() => showSensitivityModal=true}>Sensitivity Testing</button>
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
    {#each Object.keys(scenarios) as s, i}
      {#if i===0}
        <option selected value={s}>{s}</option>
      {:else}
        <option value={s}>{s}</option>
      {/if}
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

{#if showSensitivityModal}
<div class="overlay"></div>
<div id="sensitivity-modal" class="modal">

  <div id="sensitivity-modal-title">
    <div class="modal-title">
      <span>Sensitivity Testing</span>
      <button class="close" onclick={() => showSensitivityModal=false}>close</button>
      {#if sensitivityError}
        <div class="error">{sensitivityError}</div>
      {/if}
    </div>
  </div>
  
  <div id="sensitivity-chart-container" class="chart chart-wrapper" class:hidden={!sensitivityResults} bind:clientWidth={sensitivityChartWidth}>
    <div class="sensitivity-chart" bind:this={sensitivityChartContainer}></div>
    <div class="sensitivity-chart" bind:this={sensitivityChartContainer1}></div>
  </div>

  <div id="sensitivity-form">
    <div>
      <label for="sensitivity-mode-select">Mode</label>
      <select id="sensitivity-mode-select" bind:value={sensitivityMode} onchange={updateSensitivityMode}>
        {#each Object.values(SENSITIVITY_MODES) as s,i}
          {#if i===0}
            <option selected>{s}</option>
          {:else}
            <option>{s}</option>
          {/if}
        {/each}
      </select>
    </div>
    
    {#if sensitivityMode === 'heatmap'}
      <div>
        <label for="sensitivity-z-var">Z Variable</label>
        <select name="sensitivity-z-var" id="sensitivity-z-var" bind:value={sensitivityZVariable}>
          {#each Object.entries(statefulVariables) as [pyName, varData]}
              <option value={pyName}>{varData.real_name}</option>
          {/each}
        </select>
      </div>

      <div>
        <label for="sensitivity-y-var">Y-Axis / Dependent Variable (required)</label>
        <select
          id="sensitivity-y-var"
          bind:value={sensitivityYVariable}
          onchange={() => sensitivityError = ''}
        >
          <option value={null}>Select variable...</option>
          {#each Object.entries(constantVariables) as [pyName, varData]}
            <option value={pyName}>{varData.real_name}</option>
          {/each}
        </select>
      </div>

      {#if sensitivityYVariable !== 'time'}
        <div>
          <label>{sensitivityYVariable} Range</label>
          <input
            type="number"
            placeholder="Min"
            bind:value={sensitivityYRange.min}
            onchange={() => sensitivityError = ''}
          />
          <input
            type="number"
            placeholder="Max"
            bind:value={sensitivityYRange.max}
            onchange={() => sensitivityError = ''}
          />
        </div>
      {/if}
    {:else}
    <div>
      <label for="sensitivity-y-var">Y Variable</label>
      <select
        id="sensitivity-y-var"
        bind:value={sensitivityYVariable}
        onchange={() => sensitivityError = ''}
      >
        <option value={null}>Select variable...</option>
        {#each Object.entries(statefulVariables) as [pyName, varData]}
          <option value={pyName}>{varData.real_name}</option>
        {/each}
      </select>
    </div>
    {/if}

    <div>
      <label for="sensitivity-x-var">X Variable</label>
      <select
        id="sensitivity-x-var"
        bind:value={sensitivityXVariable}
      >
        <option value="time">Time (default)</option>
        {#each Object.entries(constantVariables) as [pyName, varData]}
          <option value={pyName}>{varData.real_name}</option>
        {/each}
      </select>
    </div>

    {#if sensitivityXVariable !== 'time'}
      <div>
        <label>{sensitivityXVariable} Range</label>
        <input
          type="number"
          placeholder="Min"
          bind:value={sensitivityXRange.min}
          onchange={() => sensitivityError = ''}
        />
        <input
          type="number"
          placeholder="Max"
          bind:value={sensitivityXRange.max}
          onchange={() => sensitivityError = ''}
        />
      </div>
    {/if}

    <div>
      <label for="sensitivity-step">Partitions</label>
      <input type="number" min="2" step="1" name="sensitivity-step" id="sensitivity-step" bind:value={sensitivityStep}>
    </div>
  
    {#if sensitivityStatus === 'done' && sensitivityResults}
      <button onclick={downloadSensitivityResults}>Download Results</button>
    {/if}
  
    <button
      onclick={runSensitivityAnalysis}
      disabled={sensitivityStatus === 'running'}
    >
      {sensitivityStatus === 'running' ? 'Running...' : 'Run Sensitivity Analysis'}
    </button>
  
    {#if sensitivityStatus === 'done'}
      <span>CONFETTI!</span>
    {/if}
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
                func={runSimulation}
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
              func={runSimulation}
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
    min-width: 60vw;
    min-height: 60vh;
    max-width: 80vw;
    max-height: 80vh;
    width: fit-content;
    height: fit-content;
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
  #sensitivity-modal {
    display: grid;
    grid-template-rows: 10% 90%;
    grid-template-columns: 70% 30%;
    grid-template-areas: 'title title' 'chart form';
  }
  #sensitivity-modal-title {
    grid-area: title;
  }
  #sensitivity-chart-container {
    display: flex;
    flex-direction: column;
    grid-area: chart;
    height: 100%;
    width: 100%;
    max-width: 100%;
  }
  #sensitivity-form {
    grid-area: form;
  }
  .sensitivity-chart {
    flex: 1;
    width: max-content;
    max-width: 100%;
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