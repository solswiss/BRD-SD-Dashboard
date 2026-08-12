<script>
	import './app.css';
	import { onMount } from 'svelte';
	import { title, footnote } from '../settings.json';
	import colors from '../colors.json';
	import charts from '../charts.json';
	import "carbon-components-svelte/css/white.css";
	import InputField from '../components/Input.svelte';
	import * as Tabs from "$lib/components/ui/tabs"
	import * as ToggleGroup from "$lib/components/ui/toggle-group"
	import { Label } from "$lib/components/ui/label"
	import { Input } from "$lib/components/ui/input"
	import { Button } from "$lib/components/ui/button"
	import * as Select from "$lib/components/ui/select";
	import MultiSelect from 'svelte-multiselect';
	import { RangeSlider } from "carbon-components-svelte";
	// import { Input } from "flowbite-svelte"
    import { Tooltip } from 'bits-ui';
    import InputGroup from '$lib/components/ui/input-group/input-group.svelte';
    import { HugeiconsIcon } from '@hugeicons/svelte';
    import { Add, AddIcon, Check, CheckIcon, CoinsSwapIcon, Delete01Icon, Send } from '@hugeicons/core-free-icons';
    import { Checkbox } from '$lib/components/ui/checkbox';

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
	let labToggle = $state(false);
	let labType = $state("scenario")
	let inputScenarioName = $state('10A');
	let ephScenario = $state(SCENARIO_BASELINE);
	let scenarios = { [SCENARIO_BASELINE]: { 'controls': {}, 'inputs': {} } };
	let scenario = $state(SCENARIO_BASELINE);
	let scenarioTaskComplete = $state(false);
	let selectedScenarios = $state([SCENARIO_BASELINE]);
	let kpiGroups = $state(['']);
	let activeKpiGroup = $state('');

	let loadingSimulation = $state(false);
	let isInitializing = $state(true);
	let sensitivityChartContainer = $state(null);
	let sensitivityChartContainer1 = $state(null);
	let chartContainer = $state(null);
	let loadingChart = $state(true);
	let kpiContainer = $state(null);
	let Plotly = $state(null);

	const unitsCache = new Map();
	const fetchCache = new Map();

	// Sensitivity testing state
	let statefulVariables = $state({});
	let constantVariables = $state({});
	let sensitivityMode = $state('parametric');
	let sensitivityYVariable = $state(null);
	let sensitivityXVariable = $state('time');
	let sensitivityZVariable = $state(null);
	let sensitivityXRange = $state({ min: null, max: null });
	let sensitivityYRange = $state({ min: null, max: null });
	let sensitivityStep = $state(2);
	let sensitivityResults = $state(null);
	let sensitivityStatus = $state('idle'); // idle, running, done
	let sensitivityError = $state('');

	$effect(() => {
		//console.debug('updaing inputs',inputs['treatment_dosage'],scenarios[scenario].inputs['treatment_dosage'])
		const snapshot = $state.snapshot(inputs);
		scenarios[scenario]['inputs'] = snapshot;
		//console.debug('2: updaing inputs',inputs['treatment_dosage'],scenarios[scenario].inputs['treatment_dosage'])
		if (selectedScenarios.length === 0) selectedScenarios = [SCENARIO_BASELINE];
	});

	$effect(() => {
		if (labToggle) {
			console.log('lab',labToggle)
			console.log('mode',sensitivityMode)
			
			if (sensitivityXVariable !== 'time') {
				const sensX = constantVariables[sensitivityXVariable];
				sensitivityXRange.min = sensX.min;
				sensitivityXRange.max = sensX.max;
			}

			if (sensitivityYVariable && sensitivityMode === 'heatmap') {
				try {
					const sensY = constantVariables[sensitivityYVariable];

					sensitivityYRange.min = sensY.min;
					sensitivityYRange.max = sensY.max;
				} catch(err) {
					console.log(err);
				}
			}
		}
	})

	$effect(() => {
		console.debug(`loading ${chart}?`,$state.snapshot(loadingChart))
	})


	onMount(async () => {
		const mod = await import('plotly.js-dist-min');

		Plotly = mod.default;

		await Promise.all([
			fetchMetadata(),
			fetchBaseline(),
			fetchDomains()
		]);

		// for some, order matters -- could just merge all
		await fetchGlobals();
		await setInputs();
		await runSimulation();
		isInitializing = false;
		loadingChart = false;
	});

	async function fetchMetadata() {
		try {
			const data = await fetchWithCache('/api/metadata');

			statefulVariables = { ...data.statefuls };
			constantVariables = { ...data.constants };
		} catch(err) {
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
		} catch(err) {
			errorMessage = `Failed to fetch from ${url}`;
			isInitializing = false;

			throw err;
		}
	}

	async function fetchBaseline() {
		try {
			const data = await fetchWithCache('/api/baseline_parameters');

			scenarios[SCENARIO_BASELINE] = { 'controls': data.controls, 'inputs': data.inputs };
		} catch(err) {
			errorMessage = "Could not load baseline parameters.";
			isInitializing = false;
		}
	}

	async function fetchGlobals() {
		try {
			const data = await fetchWithCache('/api/globals');
			globals = data.globals;
			console.debug('globals',globals)
			kpiGroups = data.kpi_groups;
			activeKpiGroup = kpiGroups[0];
		} catch(err) {
			errorMessage = "Could not load input globals.";
			isInitializing = false;
		}
	}

	async function fetchDomains() {
		try {
			const data = await fetchWithCache('/api/domains');

			domains = data;
			views = ["All Views", ...Object.keys(domains)];
		} catch(err) {
			errorMessage = "Could not load input domains.";
			isInitializing = false;
		}
	}

	async function runSimulation(event) {
		console.debug('running from',event ? event.target : 'no event');
		console.debug('inputs',inputs['treatment_dosage'])
		console.debug('inputs for',scenario,'vs',ephScenario,scenarios[scenario].inputs['treatment_dosage'])
		if (Object.keys(inputs).length < Object.keys(constantVariables).length) {
			console.log('Exiting runSimulation: inputs not ready.')
			return
		}
		loadingSimulation = true;
		errorMessage = "";

		let finalTime = inputs.final_time;
		const initialTime = inputs.initial_time;

		if (finalTime <= initialTime) {
			finalTime = initialTime + 1;
		}

		const inputsDraft = Object.fromEntries(Object.entries(scenarios).map(([k, v]) => [k, v.inputs]));

		try {
			console.debug(inputsDraft)
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

			if (response.ok && data) {
				simulationResults = data;
				renderChart(event);
				loadKpiPlots(event);
			} else {
				console.debug(data.error || "Simulation failed.");
			}
		} catch(err) {
			errorMessage = "Could not communicate with backend.";
			console.error(err);
		} finally {
			loadingSimulation = false;
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

	async function resetInput(pyName, newValue) {
		inputs[pyName] = newValue
		scenarios[scenario]['inputs'][pyName] = newValue;
		runSimulation()
	}

	async function createScenario() {
		const snapshot = $state.snapshot(inputs);
		scenarios[ephScenario] = {
			'controls': {
				'initial_time': inputs.initial_time,
				'final_time': inputs.final_time,
				'time_step': inputs.time_step
			},
			'inputs': snapshot
		};
		scenario = ephScenario;
		scenarioTaskComplete = true
		console.debug('switched to',$state.snapshot(scenario))
		if (!selectedScenarios.includes(scenario)) selectedScenarios.push(scenario);
		await runSimulation('create');
	}

	async function loadScenario() {
		scenario = ephScenario
		inputs = scenarios[scenario]['inputs'];
		scenarioTaskComplete = true
		console.debug('switched to',$state.snapshot(scenario))
		if (!selectedScenarios.includes(scenario)) selectedScenarios.push(scenario);
		await runSimulation('load');
	}

	async function deleteScenario() {
		if (ephScenario === SCENARIO_BASELINE) {
			errorMessage = "Cannot delete the Baseline scenario.";
			console.log(errorMessage)
			return;
		}
		if (scenario === ephScenario) {
			scenario = SCENARIO_BASELINE;
			inputs = scenarios[scenario]['inputs'];
			delete scenarios[ephScenario]
			ephScenario = scenario
			scenarioTaskComplete = true
			await runSimulation('deleteScenario: revert to baseline');
		} else {
			delete scenarios[ephScenario]
			scenarioTaskComplete = true
		}
		console.debug('switched to',$state.snapshot(scenario))
		selectedScenarios.splice(selectedScenarios.indexOf(ephScenario), 1);
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
					'time_step': inputs.time_step
				},
				'inputs': data
			};

			scenario = inputScenarioName;
			ephScenario = scenario;
			await runSimulation('import');
		} catch {
			errorMessage = "Failed to import scenario.";
			console.debug(errorMessage)
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
		const constCheck = constantVariables[pyName];

		if (constCheck) return constCheck.real_name;

		const stateCheck = statefulVariables[pyName];

		if (stateCheck) return stateCheck.real_name;

		//const auxCheck = 
		return pyName.split("_").map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
	}

	async function loadKpiPlots(event) {
		if (!kpiContainer || !Plotly) return;
		console.debug('kpi from', event ? event.target : 'no event')
		try {
			const response = await fetch(`/api/kpi_plots?q=${activeKpiGroup}`);
			const data = await response.json();

			if (response.ok && data.data) {
				Plotly.newPlot(kpiContainer, data.data, data.layout);
			} else {
				errorMessage = "Failed to load KPI plots.";
				console.error(response)
			}
		} catch(err) {
			console.error(err);
		}
	}

	function buildTrace(key, xData, vars, targetTracks, colors, lineType) {
		try {
			return targetTracks.filter((track) => vars[track.key] !== undefined).map((track, i) => ({
				x: xData,
				y: vars[track.key],
				type: 'scatter',
				mode: 'lines',
				name: `${key}: ${track.name}`,
				line: { dash: lineType, color: track.color, width: 2.5 },
				legendgroup: SCENARIO_BASELINE,
				showlegend: false,
				marker: { color: colors ? colors[i] : null }
			}));
		} catch(err) {
			throw Error(`While building a trace for ${key}: ${err}`);
		}
	}

	async function renderChart(event) {
		if (!Plotly || Object.keys(simulationResults[SCENARIO_BASELINE] || {}).length === 0 || !chartContainer) return;
		console.debug('rendering from',event ? event.target : 'no event');
		loadingChart = true

		const chartValues = charts[chart];
		const targetTracks = chartValues.map((e) => ({ key: e, name: e }));
		const tracksLength = targetTracks.length;
		const colorsOverflow = COLOR_SCHEME.length / tracksLength >= Object.keys(scenarios).length;
		const colorsUnderflow = COLOR_SCHEME.length < tracksLength;
		let traces = [];
		console.debug(selectedScenarios)

		try {
			for (const [i, k] of Object.keys(scenarios).filter((k) => selectedScenarios.includes(k)).entries()) {
				if (!simulationResults[k]) continue;
				console.debug(k)
				if (colorsUnderflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, LINE_TYPES[i % tracksLength])); else if (colorsOverflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, COLOR_SCHEME.slice(i * tracksLength, tracksLength), LINE_TYPES[i % tracksLength])); else traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, COLOR_SCHEME, LINE_TYPES[i % tracksLength]));
			}
		} catch (err) {
			// intentional early exit
			console.debug(err)
			console.log('Exiting renderChart.')
			return;
		}

		if (traces.length === 0) {
			errorMessage = "Warning: None of the target plotting variables were found in the model output keys. Check spelling.";
			console.debug(errorMessage)
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
			legend: {
				orientation: 'h',
				yanchor: 'top',
				y: -0.2,
				'xanchor': 'left',
				x: 0
			}
		};

		const config = {
			responsive: true,
			displaylogo: false,
			modeBarButtonsToRemove: ['select2d', 'lasso2d']
		};

		Plotly.newPlot(chartContainer, traces, layout, config, { responsive: true });
		loadingChart = false
	}

	// ============ SENSITIVITY TESTING FUNCTIONS ============
	// Update sensitivity mode and reset variable selections
	function updateSensitivityMode(newMode) {
		console.debug('going',newMode,sensitivityMode,sensitivityXVariable,sensitivityYVariable)
		if (newMode === undefined || sensitivityMode === newMode) return
		console.debug('still going')
		sensitivityResults = undefined
		sensitivityMode = newMode
		sensitivityError = '';
		sensitivityXVariable = 'time';
		sensitivityYVariable = null;
		sensitivityZVariable = null;

		if (Plotly) {
			console.debug('purging')
			Plotly.purge(sensitivityChartContainer);
			Plotly.purge(sensitivityChartContainer1);
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
		const maxStep = getMaximumStep(range);

		if (sensitivityStep > maxStep) {
			sensitivityStep = maxStep;
		}

		return { min, max, range };
	}

	// Calculate steps based on precision level
	function getStepCount() {
		if (sensitivityStep <= 0) {
			throw Error('Sensitivity step must be greater than zero.');
		}

		return sensitivityStep;
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
			yRange = validateAndNormalizeRange(sensitivityYRange.min, sensitivityYRange.max, yVarName);

			if (!yRange) return null;
			if (!validateTotalCombinations(steps, steps)) return null;

			return {
				mode: 'heatmap',
				variables: {
					[yVarName]: { min: yRange.min, max: yRange.max, steps },
					[sensitivityXVariable || 'time']: {
						min: sensitivityXRange.min,
						max: sensitivityXRange.max,
						steps
					},
					[sensitivityZVariable]: null
				}
			};
		} else {
			// Parametric: sweep only X (or time if X is not specified)
			xVarName = sensitivityXVariable || 'time';

			if (xVarName !== 'time') {
				xRange = validateAndNormalizeRange(sensitivityXRange.min, sensitivityXRange.max, xVarName);

				if (!xRange) return null;
			}

			if (!validateTotalCombinations(steps)) return null;

			const varDef = xVarName === 'time'
				? { min: inputs.initial_time, max: inputs.final_time, steps }
				: { min: xRange.min, max: xRange.max, steps };

			return {
				mode: 'parametric',
				variables: { [xVarName]: varDef, [yVarName]: null }
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
					scenario,
					baseInputs: scenarios[scenario]['inputs']
				})
			});

			const data = await response.json();
			if (data.error) {
				sensitivityError = data.error || 'sens err'
				console.debug('put me on the screen:',data.error)
				sensitivityStatus = 'idle';
				return
			}
			if (response.ok) {
				sensitivityResults = data;
				console.debug(sensitivityResults.final_values)
				sensitivityStatus = 'done';
				renderSensitivityChart();
			}
		} catch(err) {
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
		const summaryTrace = {
			x: values.map((r) => r.x_param_value),
			y: values.map((r) => r.y_final_value),
			type: 'scatter',
			mode: 'lines+markers',
			name: `${yVar} vs ${xVar}`,
			line: { color: '#000', width: 3 },
			marker: { size: 8 }
		};

		const realX = getRealName(xVar);
		const realY = getRealName(yVar);

		const layout = {
			hovermode: 'closest',
			title: { text: `${realX} vs ${realY}` },
			xaxis: { title: { text: realX } },
			yaxis: { title: { text: realY } },
			margin: { l: margin, r: margin, t: margin, b: margin }
		};

		const config = {
			responsive: true,
			displaylogo: false,
			modeBarButtonsToRemove: ['select2d', 'lasso2d']
		};

		Plotly.newPlot(sensitivityChartContainer1, [summaryTrace], layout, config);
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
			line: { color: COLOR_SCHEME[idx % COLOR_SCHEME.length], width: 1.5 }

			//xaxis: 'Time (days)',
			//yaxis: yVar,
		}));

		const realY = getRealName(sensitivityResults.y_variable);
		let margin = 50;

		const layout = {
			hovermode: 'closest',
			title: { text: `Sensitivity — ${realY}` },
			xaxis: { title: { text: 'Time' } },
			yaxis: { title: { text: realY } },
			margin: { l: margin, r: margin, t: margin, b: margin }
		};

		const config = {
			responsive: true,
			displaylogo: false,
			modeBarButtonsToRemove: ['select2d', 'lasso2d']
		};

		Plotly.newPlot(sensitivityChartContainer, timeSeriesTraces, layout, config);
		renderSensitivitySummary(sensitivityResults.final_values, xVar, yVar, margin);
	}

	// Render heatmap sensitivity plot
	function renderSensitivityHeatmap() {
		let trace = {
			z: sensitivityResults.grid.z_values,
			x: sensitivityResults.grid.x_values,
			y: sensitivityResults.grid.y_values,
			type: 'heatmap',
			colorscale: 'Viridis'
		};

		if (sensitivityStep <= 10) {
			trace = {
				z: sensitivityResults.grid.z_values,
				x: sensitivityResults.grid.x_values,
				y: sensitivityResults.grid.y_values,
				text: sensitivityResults.z_values_rounded,
				texttemplate: '%{text}',
				type: 'heatmap',
				colorscale: 'Viridis'
			};
		}

		let margin = 30;
		const realX = getRealName(sensitivityResults.x_variable);
		const realY = getRealName(sensitivityResults.y_variable);

		const layout = {
			title: { text: `${realX} and ${realY}` },
			xaxis: { title: { text: realX } },
			yaxis: { title: { text: realY } },
			margin: { l: margin, r: margin, t: margin, b: margin }
		};

		const config = {
			responsive: true,
			displaylogo: false,
			modeBarButtonsToRemove: ['select2d', 'lasso2d']
		};

		Plotly.newPlot(sensitivityChartContainer, [trace], layout, config);
	}

	  // Download sensitivity results as JSON
	function downloadSensitivityResults() {
		const blob = new Blob([JSON.stringify(sensitivityResults, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement('a');
		link.href = url;
		link.download = `sensitivity_${sensitivityMode}_${Date.now()}.json`;
		link.click();
		URL.revokeObjectURL(url);
	}

</script>

{#if errorMessage}
	<p class="error">{errorMessage}</p>
{/if}

<nav>
	<div class="nav-wrapper">
		<div class="brand"><span>LOGO</span><span>{title}</span></div>
		<div class="nav-options-wrapper">
			<Button onclick={() => labToggle = !labToggle}>Lab</Button>
		</div>
	</div>
</nav>

<main class="main">
	{#if labToggle}
		<div id="lab-page" class="main-page">
			<div class="main-display">
				<div class="main-display-wrapper" class:hidden={!sensitivityResults}>
					<div class="sensitivity-chart" bind:this={sensitivityChartContainer}></div>
					<div class="sensitivity-chart" bind:this={sensitivityChartContainer1}></div>
				</div>
			</div>

			<div class="main-sidebar">
				<div class="main-sidebar-wrapper">
					<Tabs.Root bind:value={labType}>
						<Tabs.List>
							<Tabs.Trigger value="scenario">Scenario Testing</Tabs.Trigger>
							<Tabs.Trigger value="sensitivity">Sensitivity Analysis</Tabs.Trigger>
						</Tabs.List>
						<Tabs.Content class="grid w-full gap-[.8rem]" value="scenario">
							<div class="grid items-center gap-[.2rem]">
								<Label for="scenario-testing-select">Compare scenarios</Label>
								<MultiSelect
									id="scenario-testing-select"
									onchange={renderChart}
									bind:value={selectedScenarios}
									options={Object.keys(scenarios)}
								/>
							</div>

							<div class="grid items-center gap-[.2rem]">
								<Label for="import-file">File</Label>
								<Input id="import-file" type="file" accept=".json" />
							</div>
							<div class="grid items-center gap-[.2rem]">
								<Label>Scenario name</Label>
								<Input
									class="max-w-xs"
									type="text"
									bind:value={inputScenarioName}
								/>
							</div>
							<Button onclick={importScenario}>Import</Button>
						</Tabs.Content>

						<Tabs.Content value="sensitivity" class="grid w-full gap-[.8rem]">
							<div class="grid items-center gap-[.2rem]">
								<Label for="sensitivity-mode-select">Mode</Label>
								<ToggleGroup.Root id="sensitivity-mode-select" value={sensitivityMode} onValueChange={updateSensitivityMode} type="single" variant="outline" spacing={2}>
									{#each SENSITIVITY_MODES as s}
										<ToggleGroup.Item value={s}>{s}</ToggleGroup.Item>
									{/each}
								</ToggleGroup.Root>
							</div>
							
							{#if sensitivityMode === 'heatmap'}
								<div class="grid items-center gap-[.2rem]">
									<Label for="sensitivity-z-var">Z Variable</Label>
									<Select.Root type="single"
										id="sensitivity-z-var"
										bind:value={sensitivityZVariable}>
										<Select.Trigger>{sensitivityZVariable ?? "Select a Z variable"}</Select.Trigger>
										<Select.Content class="z-[99] max-h-[10rem]">
											{#each Object.entries(statefulVariables) as [pyName, varData]}
												<Select.Item value={pyName} label={varData.real_name}>{varData.real_name}</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								</div>
								<div class="grid items-center gap-[.2rem]">
									<Label for="sensitivity-y-var">Y Variable</Label>
									<Select.Root type="single"
										id="sensitivity-y-var"
										bind:value={sensitivityYVariable}>
										<Select.Trigger>{sensitivityYVariable ?? "Select a Y variable"}</Select.Trigger>
										<Select.Content class="z-[99] max-h-[10rem]">
											{#each Object.entries(constantVariables) as [pyName, varData]}
												<Select.Item value={pyName}>{varData.real_name}</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								</div>
								{#if sensitivityYVariable && sensitivityYVariable !== 'time'}
								<div class="grid items-center gap-[.2rem]">
									<Label>{sensitivityYVariable} range</Label>
									<RangeSlider hideTextInput labelText={sensitivityYVariable} bind:value={sensitivityYRange.min} bind:valueUpper={sensitivityYRange.max} min={inputs[sensitivityYVariable].min ?? 0} max={inputs[sensitivityYVariable].max ?? 1} step={inputs[sensitivityYVariable].step ?? .1}/>
								</div>
								{/if}
							{:else}
							<div class="grid items-center gap-[.2rem]">
								<Label for="sensitivity-y-var">Y Variable</Label>
								<Select.Root type="single"
									id="sensitivity-y-var"
									bind:value={sensitivityYVariable}>
									<Select.Trigger>{sensitivityYVariable ?? "Select a Y variable"}</Select.Trigger>
									<Select.Content class="z-[99] max-h-[10rem]">
										{#each Object.entries(statefulVariables) as [pyName, varData]}
											<Select.Item value={pyName}>{varData.real_name}</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							</div>
							{/if}
							
							<div class="grid items-center gap-[.2rem]">
								<Label for="sensitivity-x-var">X Variable</Label>
								<Select.Root type="single"
									id="sensitivity-x-var"
									bind:value={sensitivityXVariable}>
									<Select.Trigger>{sensitivityXVariable ?? "Select a X variable"}</Select.Trigger>
									<Select.Content class="z-[99] max-h-[10rem]">
										{#each Object.entries(constantVariables) as [pyName, varData]}
											<Select.Item value={pyName}>{varData.real_name}</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							</div>
							
							{#if sensitivityXVariable !== 'time'}
							<div class="grid items-center gap-[.2rem]">
								<Label>{sensitivityXVariable} range</Label>
								<RangeSlider hideTextInput labelText={sensitivityXVariable} bind:value={sensitivityXRange.min} bind:valueUpper={sensitivityXRange.max} min={inputs[sensitivityXVariable].min ?? 0} max={inputs[sensitivityXVariable].max ?? 1} step={inputs[sensitivityXVariable].step ?? .1}/>
							</div>
							{/if}	
							<div class="grid items-center gap-[.2rem]">
								<Label for="sensitivity-step">Partitions</Label>
								<Input id="sensitivity-step" class="input-number"
									type="number"
									inputmode="numeric"
									placeholder="2"
									min="2"
									step="1"
									name="sensitivity-step"
									bind:value={sensitivityStep}
								/>
							</div>
							<div class="grid items-center gap-[.2rem]">
								<Button disabled={sensitivityStatus !== 'done' || !sensitivityResults} onclick={downloadSensitivityResults}>Download Results</Button>
								<Button
									onclick={runSensitivityAnalysis}
									disabled={sensitivityStatus === 'running'}
									>{sensitivityStatus === 'running' ? 'Running...' : 'Run Sensitivity Analysis'}</Button>
							</div>
						</Tabs.Content>
					</Tabs.Root>
				</div>
			</div>
		</div>
	{/if}
	<section class="globals">
		<div class="field">
			<Label for="global-chart">Chart</Label>
			<Select.Root type="single"
				id="global-chart"
				bind:value={chart}
				onValueChange={renderChart}>
				<Select.Trigger>{chart ?? "Select a chart"}</Select.Trigger>
				<Select.Content class="z-[99] max-h-[10rem]">
					{#each Object.keys(charts) as chartOption}
						<Select.Item value={chartOption} label={chartOption}>{chartOption}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		<div class="field">
			<Label for="global-view">View</Label>
			<Select.Root type="single"
				id="global-view"
				bind:value={view}>
				<Select.Trigger>{view ?? "Select a view"}</Select.Trigger>
				<Select.Content class="z-[99] max-h-[10rem]">
					{#each Object.values(views) as viewOption}
						<Select.Item value={viewOption} label={viewOption}>{viewOption}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		<div class="field">
			<Label for="global-kpi">KPI</Label>
			<Select.Root type="single"
				id="global-kpi"
				bind:value={activeKpiGroup}
				onValueChange={loadKpiPlots}>
				<Select.Trigger>{activeKpiGroup ?? "Select a KPI"}</Select.Trigger>
				<Select.Content class="z-[99] max-h-[10rem]">
					{#each kpiGroups as kpiOption}
						<Select.Item value={kpiOption} label={kpiOption}>{kpiOption}</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		{#each Object.values(globals) as element}
			<div class="field">
				<Label for={element.py_name}>{element.real_name}</Label>
				<Input
					id={element.py_name}
					class="!w-[12ch]"
					type="number"
					min={element.min}
					max={element.max}
					bind:value={inputs[element.py_name]}
					onchange={runSimulation}
				/>
			</div>
		{/each}

		<div class="field">
			<!-- <div class="scenario-buttons">
				<Button onclick={createScenario}>Create</Button>
				<Button onclick={loadScenario}>Load</Button>
				<Button onclick={exportScenario}>Export</Button>
				<Button onclick={deleteScenario}>Delete</Button>
			</div> -->
			<Tabs.Root value="create" class="w-full" onValueChange={()=>scenarioTaskComplete=false}>
				<Tabs.List>
					<Tabs.Trigger value="create">Create</Tabs.Trigger>
					<Tabs.Trigger value="load">Load</Tabs.Trigger>
					<Tabs.Trigger value="delete">Delete</Tabs.Trigger>
				</Tabs.List>
				<Tabs.Content class="grid items-center gap-[.2rem]" value="create">
					<Label for="input-scenario">Scenario name</Label>
					<div class="flex">
						<Input id="input-scenario" class="!w-full" type="text" placeholder="New scenario" bind:value={ephScenario}/>
						<Button class="border-none" size="icon" onclick={createScenario}>
							{#if scenarioTaskComplete}
								<HugeiconsIcon icon={CheckIcon}/>
							{:else}
								<HugeiconsIcon icon={Add}/>
							{/if}
						</Button>
					</div>
					<p class="!italic !text-xs">Working: {scenario}</p>
				</Tabs.Content>
				<Tabs.Content class="grid items-center gap-[.2rem]" value="load">
					<Label for="input-scenario">Scenario name</Label>
					<div class="flex width-full">
						<Select.Root type="single"
							id="input-scenario"
							bind:value={ephScenario}
							onValueChange={()=>{if(ephScenario!=scenario)scenarioTaskComplete=false}}>
							<Select.Trigger class="!flex-grow">{ephScenario ?? "Select a scenario"}</Select.Trigger>
							<Select.Content class="z-[99] max-h-[16rem]">
								{#each Object.keys(scenarios) as scenarioOption}
									<Select.Item value={scenarioOption} label={scenarioOption}>{scenarioOption}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
						<Button class="border-none" size="icon" onclick={loadScenario}>
							{#if scenarioTaskComplete}
								<HugeiconsIcon icon={CheckIcon}/>
							{:else}
								<HugeiconsIcon icon={CoinsSwapIcon}/>
							{/if}
						</Button>
					</div>
					<p class="!italic !text-xs">Working: {scenario}</p>
				</Tabs.Content>
				<Tabs.Content class="grid items-center gap-[.2rem]" value="delete">
					<Label for="input-scenario">Scenario name</Label>
					<div class="flex width-full">
						<Select.Root type="single"
							id="input-scenario"
							bind:value={ephScenario}
							onValueChange={()=>{scenarioTaskComplete=false}}>
							<Select.Trigger class="!flex-grow w-full">{ephScenario ?? "Select a scenario"}</Select.Trigger>
							<Select.Content class="z-[99] max-h-[16rem]">
								{#each Object.keys(scenarios) as scenarioOption}
									<Select.Item value={scenarioOption} label={scenarioOption}>{scenarioOption}</Select.Item>
								{/each}
							</Select.Content>
						</Select.Root>
						<Button class="border-none" size="icon" onclick={deleteScenario}>
							{#if scenarioTaskComplete}
								<HugeiconsIcon icon={CheckIcon}/>
							{:else}
								<HugeiconsIcon icon={Delete01Icon}/>
							{/if}
						</Button>
					</div>
					<p class="!italic !text-xs">Working: {scenario}</p>
				</Tabs.Content>
			</Tabs.Root>
		</div>
	</section>

	<section class="displays">
		<section
			class="chart chart-wrapper relative"
			class:hidden={!simulationResults}
		>
			<div class="loading-skeleton" disabled={loadingChart}></div>
			<div bind:this={chartContainer} class="plotly-target"></div></section>
		<section bind:this={kpiContainer} class="kpi-wrapper"></section>
	</section>

	<Tooltip.Provider>
	<section class="inputs">
		{#if view === "All Views"}
			<section class="input-group columns">
				{#each Object.entries(domains) as [domainName, elements]}
					<div class="input-column column">
						<button
							class="domain-header"
							onclick={() => view = domainName}
						>{domainName}</button>

						{#each elements as element}
							<InputField
								obj={element}
								bind:obj_of_inputs={inputs[element.py_name]}
								default_value={scenarios[SCENARIO_BASELINE]['inputs'][element.py_name]}
								func={runSimulation}
								resetInput={resetInput}
							/>
						{/each}
					</div>
				{/each}
			</section>
		{:else}
			<section class="input-column column">
				<div class="input-header">
					<span>{view}</span>

					<button
						class="domain-header"
						onclick={() => view = "All Views"}
					>[All Views]</button>
				</div>

				<div
					style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));"
				>
					{#each Object.values(domains[view]) as element}
						<InputField
							obj={element}
							bind:obj_of_inputs={inputs[element.py_name]}
							default_value={scenarios[SCENARIO_BASELINE]['inputs'][element.py_name]}
							func={runSimulation}
							resetInput={resetInput}
						/>
					{/each}
				</div>
			</section>
		{/if}
	</section>
	</Tooltip.Provider>
</main>
<footer>{footnote}</footer>

<style>
@reference "tailwindcss";

	footer {
		padding: .5rem .8rem;
	}

	.field {
		display: flex;
		flex-direction: row;
		justify-content: space-between;
		align-items: start;
		.input-scenario {
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

	nav {
		position: fixed;
		width: 100vw;
		height: 2.75rem;
		z-index: 99;
		background: #fff;
	}

	.nav-wrapper {
		display: flex;
		justify-content: space-between;
		padding: .8rem;
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

	#lab-page {
		display: grid;
		grid-template-rows: 1fr 1fr;
		grid-template-columns: 30% 70%;
		grid-template-areas: 'sidebar display' 'sidebar display';
	}

	.main-sidebar {
		grid-area: sidebar;
	}
	.main-sidebar-wrapper {
		height: 100%;
		padding: .8rem;
	}
	.main-display {
		display: flex;
		flex-direction: column;
		grid-area: display;
		height: 100%;
		width: 100%;
	}

	.sensitivity-chart {
		flex: 1;
		width: max-content;
		max-width: 100%;
	}

	.loading-skeleton:disabled {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
		background-size: 200% 100%;
		animation: shimmer 1.5s infinite;
		z-index: 10;
	}
	@keyframes shimmer {
		0% { background-position: 200% 0; }
		100% { background-position: -200% 0; }
	}

	.hidden {
		display: none;
	}

	.main {
		flex: 1;
		background: white;
		font-size: 16px;
		color: #000;
		padding-top: 2.75rem;
		display: grid;
		grid-template-columns: 20% 80%;
		grid-template-areas: "globals displays" "inputs inputs";
		gap: 0;
		padding: 3em 0;
		> * {
			background: white;
		}
	}

	.main-page {
		width: 100%;
		height: 100%;
		position: fixed;
		top: 0;
		left: 0;
		z-index: 98;
		padding-top: 2.75rem;
	}

	.globals {
		grid-area: globals;
		display: flex;
		flex-direction: column;
		padding: 12px;
		gap: 12px;
		.global-number-input {
			width: 10ch;
			max-width: fit-content;
		}
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
		gap: 1.6rem;
	}

	.column {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: .5rem;
	}
</style>
