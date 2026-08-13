<script>
	import './app.css';
	import { onMount } from 'svelte';
	import { title, footnote } from '../settings.json';
	import colors from '../colors.json';
	import charts from '../charts.json';
	import chroma from 'chroma-js'
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
    import { Tooltip } from 'bits-ui';
    import { HugeiconsIcon } from '@hugeicons/svelte';
    import { Add, CheckIcon, CoinsSwapIcon, Delete01Icon, Download, FileExportIcon, FileImportIcon, MoreHorizontalCircle02FreeIcons, MoreHorizontalCircle02Icon, MoreVerticalFreeIcons, MoreVerticalIcon, TestTube01Icon } from '@hugeicons/core-free-icons';
	import { FileUploaderButton } from 'carbon-components-svelte';
    import { Spinner } from '$lib/components/ui/spinner';

	// Constants
	const SCENARIO_BASELINE = 'Baseline';

	const DEFAULT_TIME_STEP = 0.0625;
	const COLOR_SCHEME = colors.scheme;
	const LINE_TYPES = ['solid', 'dashdot', 'dot'];
	const SENSITIVITY_MODES = ['parametric', 'heatmap'];
	const MIN_STEP_VALUE = 0.1;
	const STANDOFF = 20;

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
	let connected = $state(false)
	let errorMessage = $state("");
	let labToggle = $state(false); //TODO: undo me
	let labType = $state("scenario")
	let ephScenario = $state(SCENARIO_BASELINE);
	let newScenario = $state("");
	let scenarios = { [SCENARIO_BASELINE]: { 'controls': {}, 'inputs': {} } };
	let scenario = $state(SCENARIO_BASELINE);
	let scenarioTaskComplete = $state(false);
	let scenarioImportComplete = $state(false)
	let scenarioExportComplete = $state(false)
	let scenarioImportFiles = $state([])
	let selectedScenarios = $state([SCENARIO_BASELINE]);
	let selectedScenarioTestingVariables = $state(null)
	let kpiGroups = $state(['']);
	let activeKpiGroup = $state('');

	let loadingSimulation = $state(false);
	let simulationOK = false;
	let isInitializing = $state(true);
	let scenarioChartContainer = $state(null)
	let sensitivityChartContainer = $state(null);
	let sensitivityChartContainer1 = $state(null);
	let sensitivityOK = false;
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
		// syncs inputs (very important)
		const snapshot = $state.snapshot(inputs);
		scenarios[scenario]['inputs'] = snapshot;
		if (selectedScenarios.length === 0) selectedScenarios = [SCENARIO_BASELINE];
	});

	$effect(()=>{
		if (!isInitializing && Object.keys(constantVariables).length > 0) {
			if (sensitivityXVariable !== 'time') {
				sensitivityXRange.min = constantVariables[sensitivityXVariable].min
				sensitivityXRange.max = constantVariables[sensitivityXVariable].max
			}
			if (sensitivityMode === 'heatmap' && sensitivityYVariable) {
				sensitivityYRange.min = constantVariables[sensitivityYVariable].min
				sensitivityYRange.max = constantVariables[sensitivityYVariable].max
			}
		}
	})

	// if (typeof window !== 'undefined') {
	// 	window.setSkeleton = (val) => {
	// 		loadingChart = true
	// 	};
	// }

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

		if (!errorMessage) connected = true
		else return
		console.debug(isInitializing,'connected',connected)

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
			globals = JSON.parse(data.globals);
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

	async function runSimulation(event='no event', target='main') {
		console.debug('running from',event.target ? event.target : event);
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

		const inputsDraft = Object.fromEntries(Object.entries(scenarios).map(([k, v]) => [k, v.inputs])); // runs for all scenarios
		
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
			console.debug('data is',data)
			console.debug('response is',response.ok)
			if (!response.ok) {
				simulationOK = false
				const errorData = await response.json().catch(() => ({}));
				console.error("Error running simulation:",errorData || "???")
			} else {
				simulationOK = true
				simulationResults = data;
				if (target === 'scenario') renderScenarioChart()
				else {
					renderChart(event);
					loadKpiPlots(event);
				}
			}
		} catch(err) {
			simulationOK = false
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
		if (newScenario === "" || !newScenario || newScenario.length === 0) {
			console.debug('empty name',newScenario)
			errorMessage = "Scenario name cannot be empty."
			return
		}
		const snapshot = $state.snapshot(inputs);
		scenarios[newScenario] = {
			'controls': {
				'initial_time': inputs.initial_time,
				'final_time': inputs.final_time,
				'time_step': inputs.time_step
			},
			'inputs': snapshot
		};
		scenario = newScenario;
		ephScenario = scenario;
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
			selectedScenarios.splice(selectedScenarios.indexOf(ephScenario), 1);
			ephScenario = scenario
			scenarioTaskComplete = true
			await runSimulation('deleteScenario: revert to baseline');
		} else {
			delete scenarios[ephScenario]
			selectedScenarios.splice(selectedScenarios.indexOf(ephScenario), 1);
			scenarioTaskComplete = true
			ephScenario = scenario
		}
		console.debug('scenarios:',Object.keys(scenarios))
		console.debug('selected scenarios',selectedScenarios)
		console.debug('switched to',$state.snapshot(scenario))
	}

	async function importScenario() {
		try {
			if (newScenario === "" || !newScenario || newScenario.length === 0) {
				errorMessage = "Scenario name cannot be empty."
				return
			}
			const file = scenarioImportFiles[0]
			if (!file) {
				errorMessage = "No file uploaded"
				console.debug(errorMessage)
				return;
			}
			const text = await file.text();
			const data = JSON.parse(text);
			scenarios[newScenario] = {
				'controls': {
					'initial_time': inputs.initial_time,
					'final_time': inputs.final_time,
					'time_step': inputs.time_step
				},
				'inputs': data
			};
			scenario = newScenario;
			ephScenario = scenario;
			scenarioImportComplete = true
			if (!selectedScenarios.includes(scenario)) selectedScenarios.push(scenario)
			await runSimulation('import');
		} catch {
			errorMessage = "Failed to import file.";
			console.debug(errorMessage)
		}
	}

	function exportScenario() {
		const blob = new Blob([JSON.stringify(inputs, null, 2)], { type: 'application/json' });
		const url = URL.createObjectURL(blob);
		const link = document.createElement("a");

		link.href = url;
		link.download = `scenario_${ephScenario}_${Date.now()}.json`
		scenarioExportComplete = true
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

	function buildTrace(key, xData, vars, targetTracks, colors, lineType, showLegend=false) {
		try {
			return targetTracks.filter((track) => vars[track.key] !== undefined).map((track, i) => ({
				x: xData,
				y: vars[track.key],
				type: 'scatter',
				mode: 'lines',
				name: `${key}: ${track.name}`,
				line: { dash: lineType, color: track.color, width: 2.5 },
				legendgroup: SCENARIO_BASELINE,
				showlegend: showLegend,
				marker: { color: colors ? colors[i] : null },
				hoverlabel: {namelength:-1} // to avoid truncation
			}));
		} catch(err) {
			throw Error(`While building a trace for ${key}: ${err}`);
		}
	}

	async function renderChart(event) {
		if (!Plotly || !simulationOK || Object.keys(simulationResults[SCENARIO_BASELINE] || {}).length === 0 || !chartContainer) return;
		console.debug('rendering from',event ? event.target : 'no event');
		loadingChart = true

		const chartValues = charts[chart];
		const targetTracks = chartValues.map((e) => ({ key: e, name: e }));
		const tracksLength = targetTracks.length;
		const colorsOverflow = COLOR_SCHEME.length / tracksLength >= Object.keys(scenarios).length;
		const colorsUnderflow = COLOR_SCHEME.length < tracksLength;
		let traces = [];

		try {
			for (const [i, k] of Object.keys(scenarios).filter((k) => selectedScenarios.includes(k)).entries()) {
				if (!simulationResults[k]) continue;
				if (colorsUnderflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, LINE_TYPES[i % tracksLength])); 
				else if (colorsOverflow) traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, COLOR_SCHEME.slice(i * tracksLength, tracksLength), LINE_TYPES[0])); 
				else traces.push(...buildTrace(k, simulationResults[k].time, simulationResults[k].variables, targetTracks, COLOR_SCHEME, LINE_TYPES[i % tracksLength]));
			}
		} catch (err) {
			// intentional early exit
			console.debug('RenderChart',err)
			console.log('Exiting renderChart.')
			return;
		}

		if (traces.length === 0) {
			errorMessage = "Warning: None of the target plotting variables were found in the model output keys. Check spelling.";
			console.debug(errorMessage)
			return;
		}

		// TODO: check unified units
		let yunits = await getUnits(chartValues[0]);
		const layout = {
			title: { text: chart, font: { size: 18 }, standoff: STANDOFF },
			xaxis: { title: { text: 'Time (Days)', standoff: STANDOFF }, gridcolor: '#f0f0f0', automargin: true },
			yaxis: { title: { text: yunits, standoff: STANDOFF }, gridcolor: '#f0f0f0', automargin: true },
			margin: { t: 50, b: 50, l: 60, r: 20 },
			//hovermode: 'x unified',
			plot_bgcolor: '#ffffff',
			paper_bgcolor: '#ffffff',
			autosize: true,
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

		if (isInitializing) Plotly.newPlot(chartContainer, traces, layout, config);
		else Plotly.react(chartContainer, traces, layout, config);
		loadingChart = false
	}

	function goToMain() {
		console.debug("going to main")
		labToggle = false
	}

	// ============ SENSITIVITY TESTING FUNCTIONS ============
	async function runScenarioTest(event) {
		runSimulation(event, 'scenario')
	}

	async function renderScenarioChart() {
		//selectedScenarioTestingVariables
		if (!Plotly || !simulationOK || Object.keys(simulationResults[SCENARIO_BASELINE] || {}).length === 0 || !scenarioChartContainer || selectedScenarioTestingVariables.length === 0) return;
		const results = $state.snapshot(simulationResults)
		const vars = $state.snapshot(selectedScenarioTestingVariables)
		const targetTracks = vars.map(v => ({key: v, name: v}));
		const tracksLength = targetTracks.length;
		const colorsOverflow = COLOR_SCHEME.length / tracksLength >= Object.keys(scenarios).length;
		const colorsUnderflow = COLOR_SCHEME.length < tracksLength;
		let traces = [];

		try {
			for (const [i, k] of Object.keys(scenarios).filter((k) => selectedScenarios.includes(k)).entries()) {
				if (!results[k]) continue;
				if (colorsUnderflow) traces.push(...buildTrace(k, results[k].time, results[k].variables, targetTracks, LINE_TYPES[i % tracksLength], true)); 
				else if (colorsOverflow) traces.push(...buildTrace(k, results[k].time, results[k].variables, targetTracks, COLOR_SCHEME.slice(i * tracksLength, tracksLength), LINE_TYPES[0], true)); 
				else traces.push(...buildTrace(k, results[k].time, results[k].variables, targetTracks, COLOR_SCHEME, LINE_TYPES[i % tracksLength], true));
			}
		} catch (err) {
			// intentional early exit
			console.debug(err)
			console.log('Exiting renderScenarioChart.')
			return;
		}

		if (traces.length === 0) {
			errorMessage = "Warning: None of the target plotting variables were found in the model output keys. Check spelling.";
			console.debug(errorMessage)
			return;
		}

		// TODO: check unified units
		let yunits = await getUnits(selectedScenarioTestingVariables[0]);
		const layout = {
			title: { text: chart, font: { size: 18 }, standoff: STANDOFF },
			xaxis: { title: { text: 'Time (Days)', standoff: STANDOFF }, gridcolor: '#f0f0f0', automargin: true },
			yaxis: { title: { text: yunits, standoff: STANDOFF }, gridcolor: '#f0f0f0', automargin: true },
			margin: { t: 50, b: 50, l: 60, r: 20 },
			//hovermode: 'x unified',
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

		Plotly.newPlot(scenarioChartContainer, traces, layout, config, { responsive: true });
	}

	// Update sensitivity mode and reset variable selections
	function updateSensitivityMode(newMode) {
		if (newMode === undefined || sensitivityMode === newMode) return
		sensitivityResults = undefined
		sensitivityMode = newMode
		sensitivityError = '';
		sensitivityXVariable = 'time';
		sensitivityYVariable = null;
		sensitivityZVariable = null;

		if (Plotly) {
			console.debug('purging')
			Plotly.purge(scenarioChartContainer)
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
			errorMessage = "Partition count has been limited to "+maxStep
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
			errorMessage = "Missing required parameters."
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
			console.debug('sens data',data)
			if (data.error) {
				sensitivityOK = false
				sensitivityError = data.error || 'Error running sensitivity analysis'
				console.debug('put me on the screen:',data.error)
				sensitivityStatus = 'idle';
				return
			}
			try {
				if (!response.ok) {
					sensitivityOK = false
					sensitivityError = data.error || 'Error running sensitivity analysis'
				} else {
					sensitivityResults = data;
					sensitivityOK = true
					renderSensitivityChart();
				}
			} catch (err) {
				sensitivityOK = false
				sensitivityError = data.error || 'Error running sensitivity analysis'
				console.error(err)
			} finally {
				sensitivityStatus = 'done';
			}
		} catch(err) {
			sensitivityError = 'Could not communicate with backend';
			console.error(err);
			sensitivityStatus = 'idle';
		}
	}

	// Render sensitivity results based on mode
	function renderSensitivityChart() {
		if (!sensitivityOK || !sensitivityResults || !Plotly || !sensitivityChartContainer) return;

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
			line: { color: COLOR_SCHEME[0], width: 3 },
			marker: { size: 8 }
		};

		const realX = getRealName(xVar);
		const realY = getRealName(yVar);

		const layout = {
			hovermode: 'closest',
			title: { text: `${realX} vs ${realY}`, standoff: STANDOFF },
			xaxis: { title: { text: realX, standoff: STANDOFF }, automargin: true },
			yaxis: { title: { text: realY, standoff: STANDOFF }, automargin: true },
			margin: { l: margin, r: margin, t: margin, b: margin },
			autosize: true,
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
		const color = chroma(COLOR_SCHEME[0])
		const colors = chroma.scale([color.darken(2.8), color.brighten(2.8)]).colors(sensitivityStep)
		// Build N traces (one per X parameter value, showing Y vs time)
		const timeSeriesTraces = sensitivityResults.time_series.map((series, idx) => ({
			x: series.time,
			y: series.y_values,
			type: 'scatter',
			mode: 'lines',
			name: `${series.x_param_value.toFixed(2)}`,
			line: { color: colors[idx], width: 1.5 }
		}));

		const realY = getRealName(sensitivityResults.y_variable);
		let margin = 50;

		const layout = {
			hovermode: 'closest',
			title: { text: `Sensitivity — ${realY}`, standoff: STANDOFF },
			xaxis: { title: { text: 'Time', standoff: STANDOFF }, automargin: true },
			yaxis: { title: { text: realY, standoff: STANDOFF }, automargin: true },
			margin: { l: margin, r: margin, t: margin, b: margin },
			autosize: true,
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
			title: { text: `${realX} and ${realY}`, standoff: STANDOFF },
			xaxis: { title: { text: realX, standoff: STANDOFF }, automargin: true },
			yaxis: { title: { text: realY, standoff: STANDOFF }, automargin: true },
			margin: { l: margin, r: margin, t: margin, b: margin },
			autosize: true,
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

<!-- {#if errorMessage}
	<p class="error">{errorMessage}</p>
{/if} -->

<div id="screen-zero" hidden={!isInitializing && connected}>
	<div class="w-full">
		<img src="https://images.emojiterra.com/google/noto-emoji/animated-emoji/1f42e.gif" alt="GIF of cow eating">
		<div class="flex !flex-col w-full">
			{#if !isInitializing && !connected}
			<span class="!text-lg !font-medium text-destructive">{errorMessage ?? "Failed to connect with server"}</span>
			<span class="!text-sm">Please try again in a few moments.</span>
			{:else}
			<span class="!text-lg">Loading...</span>
			{/if}
		</div>
	</div>
</div>

<nav>
	<div class="nav-wrapper">
		<div class="brand">
			<button class="cursor-pointer" onclick={goToMain}><img id="brand-logo" src="https://images.icon-icons.com/1507/PNG/512/preferencesdesktoplocale_103779.png" alt="globe icon"></button>
			<span id="brand-title" class="!text-[1.2rem] !font-medium">{title}</span>
		</div>
		<div class="nav-options-wrapper">
			<Button variant={labToggle?"outline":"default"} onclick={()=>{labToggle=!labToggle;if(!labToggle)runSimulation()}}>{labToggle?"Return":"Lab"}</Button>
		</div>
	</div>
</nav>

<main class="main">
	{#if labToggle}
		<div id="lab-page" class="main-page">
			<div class="main-display">
				<div class="main-display-wrapper">
				<!-- {#if labType==='sensitivity'} -->
					<div hidden={labType!=='sensitivity'} class="sensitivity-chart !w-full" bind:this={sensitivityChartContainer}></div>
					<div hidden={labType!=='sensitivity'} class="sensitivity-chart !w-full" bind:this={sensitivityChartContainer1}></div>
				<!-- {:else if labType==='scenario'} -->
					<div hidden={labType!=='scenario'} class="scenario-chart" bind:this={scenarioChartContainer}></div>
				<!-- {/if} -->
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
								<Label for="select-scenario">Export scenario</Label>
								<div class="flex width-full">
									<Select.Root type="single"
										id="select-scenario"
										bind:value={ephScenario}
										onValueChange={()=>{if(scenario!==ephScenario)scenarioExportComplete=false}}>
										<Select.Trigger class="!flex-grow">{ephScenario ?? "Select a scenario"}</Select.Trigger>
										<Select.Content class="z-[99] max-h-[16rem]">
											{#each Object.keys(scenarios) as scenarioOption}
												<Select.Item value={scenarioOption} label={scenarioOption}>{scenarioOption}</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
									<Button class="border-none" size="icon" onclick={exportScenario}>
										{#if scenarioExportComplete}
											<HugeiconsIcon icon={CheckIcon}/>
										{:else}
											<HugeiconsIcon icon={FileExportIcon}/>
										{/if}
									</Button>
								</div>
							</div>

							<div class="grid items-center gap-[.4rem]">
								<div class="grid items-center gap-[.2rem]">
									<Label for="import-file">Import Scenario</Label>
									<div class="flex h-full">
										<FileUploaderButton labelText="Add file" id="import-file" bind:files={scenarioImportFiles} type="file" accept=".json" />
										<Input id="import-scenario" class="!w-full h-full" type="text" placeholder="New scenario" bind:value={newScenario}/>
										<Button class="border-none h-full" size="icon" onclick={importScenario}>
											{#if scenarioImportComplete}
												<HugeiconsIcon icon={CheckIcon}/>
											{:else}
												<HugeiconsIcon icon={FileImportIcon}/>
											{/if}
										</Button>
									</div>
								</div>
							</div>

							<div class="grid items-center gap-[.2rem]">
								<Label for="scenario-testing-select">Compare scenarios</Label>
								<div class="multiselect">
									<MultiSelect
										id="scenario-testing-select"
										onchange={renderChart}
										bind:value={selectedScenarios}
										options={Object.keys(scenarios)}
									/>
								</div>
							</div>

							<div class="grid items-center gap-[.2rem]">
								<Label for="scenario-testing-variable-select">Watch variables</Label>
								<div class="multiselect">
									<MultiSelect
										id="scenario-testing-variable-select"
										onchange={runScenarioTest}
										bind:value={selectedScenarioTestingVariables}
										options={Object.values(statefulVariables).map(v => v.real_name)}
									/>
								</div>
							</div>
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
										<Select.Trigger class="!w-full">{sensitivityZVariable ?? "Select a Z variable"}</Select.Trigger>
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
										<Select.Trigger class="!w-full">{sensitivityYVariable ?? "Select a Y variable"}</Select.Trigger>
										<Select.Content class="z-[99] max-h-[10rem]">
											{#each Object.entries(constantVariables) as [pyName, varData]}
												<Select.Item value={pyName} label={varData.real_name}>{varData.real_name}</Select.Item>
											{/each}
										</Select.Content>
									</Select.Root>
								</div>
								{#if sensitivityYVariable && sensitivityYVariable !== 'time'}
								<div class="grid items-center gap-[.2rem]">
									<!-- <Label>{sensitivityYVariable} range</Label> -->
									<RangeSlider hideTextInput labelText={`${getRealName(sensitivityYVariable)} range`} bind:value={sensitivityYRange.min} bind:valueUpper={sensitivityYRange.max} min={constantVariables[sensitivityYVariable]["min"] ?? 0} max={constantVariables[sensitivityYVariable]["max"] ?? 1} step={constantVariables[sensitivityYVariable]["step"] ?? .1}/>
								</div>
								{/if}
							{:else}
							<div class="grid items-center gap-[.2rem]">
								<Label for="sensitivity-y-var">Y Variable</Label>
								<Select.Root type="single"
									id="sensitivity-y-var"
									bind:value={sensitivityYVariable}>
									<Select.Trigger class="!w-full">{sensitivityYVariable ?? "Select a Y variable"}</Select.Trigger>
									<Select.Content class="z-[99] max-h-[10rem]">
										{#each Object.entries(statefulVariables) as [pyName, varData]}
											<Select.Item value={pyName} label={varData.real_name}>{varData.real_name}</Select.Item>
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
									<Select.Trigger class="!w-full">{sensitivityXVariable ?? "Select a X variable"}</Select.Trigger>
									<Select.Content class="z-[99] max-h-[10rem]">
										{#each Object.entries(constantVariables) as [pyName, varData]}
											<Select.Item value={pyName} label={varData.real_name}>{varData.real_name}</Select.Item>
										{/each}
									</Select.Content>
								</Select.Root>
							</div>
							
							{#if sensitivityXVariable !== 'time'}
							<div class="grid items-center gap-[.2rem]">
								<!-- <Label>{sensitivityXVariable} range</Label> -->
								<RangeSlider hideTextInput labelText={`${getRealName(sensitivityXVariable)} range`} bind:value={sensitivityXRange.min} bind:valueUpper={sensitivityXRange.max} min={constantVariables[sensitivityXVariable]["min"] ?? 0} max={constantVariables[sensitivityXVariable]["max"] ?? 1} step={constantVariables[sensitivityXVariable]["step"] ?? .1}/>
							</div>
							{/if}	
							<div class="grid items-center gap-[.2rem]">
								<Label for="sensitivity-step">Partition Count</Label>
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
							<div class="grid grid-cols-2 items-center gap-[.2rem]">
								<Button disabled={!sensitivityOK} onclick={downloadSensitivityResults}>
									<HugeiconsIcon icon={Download}/>
									Download
								</Button>
								<Button
									onclick={runSensitivityAnalysis}
									disabled={sensitivityStatus === 'running'}
									>
									{#if sensitivityStatus==='running'}<Spinner/>
									{:else}<HugeiconsIcon icon={TestTube01Icon}/>{/if}
									{sensitivityStatus === 'running' ? 'Running...' : 'Run'}
								</Button>
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
			<Tabs.Root value="create" class="w-full" onValueChange={()=>scenarioTaskComplete=false}>
				<Tabs.List>
					<Tabs.Trigger value="create">Create</Tabs.Trigger>
					<Tabs.Trigger value="load">Load</Tabs.Trigger>
					<Tabs.Trigger value="delete">Delete</Tabs.Trigger>
				</Tabs.List>
				<Tabs.Content class="grid items-center gap-[.2rem]" value="create">
					<Label for="input-scenario">Scenario name</Label>
					<div class="flex">
						<Input id="input-scenario" class="!w-full" type="text" placeholder="New scenario" bind:value={newScenario} oninput={()=>{scenarioTaskComplete=false}}/>
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
		<div class="flex flex-row align-center max-w-[80%] !pt-3">
			<div class="flex flex-row gap-1 flex-shrink-1 !p-1 !bg-input rounded-l">
				Active scenarios
				<HugeiconsIcon icon={MoreVerticalIcon} size="16" onclick={()=>labToggle=true}/>
			</div>
			<div class="flex-grow-1 !p-1 overflow-x-auto !border !border-input rounded-r">{selectedScenarios.join(", ")}</div>
		</div>
		<section class="displays-wrapper">
			<section
				class="chart chart-wrapper relative"
				// class:hidden={!simulationResults}
				class:skeleton={loadingChart || !simulationResults}
			>
				<div hidden={loadingChart || !simulationResults} bind:this={chartContainer} class="plotly-target"></div>
			</section>
			<section bind:this={kpiContainer} class="kpi-wrapper"></section>
		</section>
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
#screen-zero {
	position: fixed;
	left: 0;
	top: 0;
	height: 100vh;
	width: 100vw;
	background-color: #fff;
	z-index: 110;
	>div {
		position: absolute;
		left: 3rem;
		bottom: 2.4rem;
		height: 6rem;
		z-index: 111;
		display: flex;
		flex-direction: row;
		align-items: flex-end;
		gap: 2rem;
		img {
			height: 6rem;
		}
	}
	
}

footer {
	padding: .5rem .8rem;
}

.field {
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: start;
}

nav {
	position: fixed;
	width: 100vw;
	height: var(--nav-height);
	z-index: 99;
	background: #fff;
}
.nav-wrapper {
	display: flex;
	align-items: center;
	justify-content: space-between;
	padding: .6rem 1.2rem;
}
nav .brand {
	display: flex;
	align-items: center;
	gap: 24px;
	#brand-logo {
		height: 2rem;
	}
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
.multiselect :global(ul.selected li) {
	padding: .2rem .35rem;
	margin: 4px !important;
}
.multiselect :global(li) {
	background-color: #0f62fe;
	padding: .25rem .35rem;
	&:hover {
		background-color: #0353e9;
	}
}
.multiselect >:global(div) {
	background-color: color-mix(in oklab, var(--input) 20%, transparent);
	border: 1px solid var(--input);
}
.multiselect :global(svg) {
	fill: var(--primary);
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
	overflow: scroll;
}
.main-display-wrapper {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	padding: 1rem;
	height: auto;
	width: 100%;
	max-width: 100%;
}

.sensitivity-chart {
	flex: 1;
	width: max-content;
	max-width: 100%;
}

.skeleton {
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
	display: grid;
	grid-template-columns: 20% 80%;
	grid-template-areas: "globals displays" "inputs inputs";
	gap: 0;
	padding: var(--nav-height) 0 3em 0;
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
}

.field {
	display: flex;
	flex-direction: row;
	width: 100%;
	flex-wrap: wrap;
}

.displays {
	grid-area: displays;
}
.displays-wrapper {
	display: grid;
	grid-template-columns: 80% 20%;
	padding: .5rem;
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
	padding: .5rem;
	margin-top: 1rem;
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
