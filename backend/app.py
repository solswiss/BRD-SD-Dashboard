from flask import Flask, request, jsonify
from flask_cors import CORS
import plotly.graph_objects as go
import pysd
import pandas as pd
import json
import numpy as np

app = Flask(__name__)
CORS(app)

model = pysd.load('model.py')
doc = model.doc

shared_state = {'results': {'time': {}, 'variables': {}}}
all_variables_df = doc.dropna(subset=['Py Name'])
all_variables = {}
kpis = {}

# Constants
KPI_TITLE_SIZE = 12
KPI_VALUE_SIZE = 28
KPI_MARGIN = 50


def init():
    """Load all variables and KPIs from model and config files."""
    for _, row in all_variables_df.iterrows():
        py_name = row['Py Name']
        try:
            default = float(getattr(model.components, py_name)())
        except:
            default = float(row['Limits'][0])

        units = (row['Units'] if row['Units'] != '1/day' else '/day') if pd.notna(row['Units']) else "UNDEF"

        min_val = float(row['Limits'][0]) if pd.notna(row['Limits'][0]) else 0
        max_val = float(row['Limits'][1]) if pd.notna(row['Limits'][1]) else (
            default * 2 if default > 1 else 1
        )

        all_variables[py_name] = {
            "py_name": py_name,
            "real_name": row['Real Name'],
            "type": row['Type'],
            "units": units,
            "min": min_val,
            "max": max_val,
            "step": 0.05 if default <= 1 else 0.1,
            "default": default
        }

    with open('kpis.json', 'r') as file:
        data = json.load(file)
        for k, v in data.items():
            kpis[k] = v


@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Return model structure: controls, auxiliaries, constants, KPI groups."""
    try:
        controls = {
            "initial_time": float(model.components.initial_time()),
            "final_time": float(model.components.final_time()),
            "time_step": float(model.components.time_step())
        }
        auxiliaries = {}
        constants = {}
        statefuls = {}
        for k, v in all_variables.items():
            if v['type'] == 'Auxiliary':
                auxiliaries[k] = v
            elif v['type'] == 'Constant':
                constants[k] = v
            elif v['type'] == 'Stateful':
                statefuls[k] = v

        return jsonify({
            "controls": controls,
            "auxiliaries": auxiliaries,
            "constants": constants,
            "statefuls": statefuls,
            "kpi_groups": list(kpis.keys())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/baseline_parameters', methods=['GET'])
def get_baseline_parameters():
    """Return default control and constant values."""
    try:
        controls = {
            "initial_time": float(model.components.initial_time()),
            "final_time": float(model.components.final_time()),
            "time_step": float(model.components.time_step())
        }
        constants = {k: v['default'] for k, v in all_variables.items() if v['type'] == 'Constant'}

        return jsonify({
            "controls": controls,
            "inputs": constants,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/globals', methods=['GET'])
def get_globals():
    """Return global input variables and KPI groups."""
    try:
        with open('globals.json', 'r') as file:
            data = json.load(file)
        
        globals_vars = {var: all_variables[var] for var in data["variables"]}
        
        return jsonify({
            'globals': globals_vars,
            'kpi_groups': list(kpis.keys())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/domains', methods=['GET'])
def get_domains():
    """Return variables grouped by domain (constants only)."""
    try:
        with open('domains.json', 'r') as file:
            data = json.load(file)
        
        constants = {k: v for k, v in all_variables.items() if v["type"] == 'Constant'}
        domains = {}
        
        for domain, variables in data.items():
            domains[domain] = [constants[var] for var in variables if var in constants]
        
        return domains
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/units', methods=['GET'])
def get_units():
    """Return units for a given variable."""
    try:
        py_name = request.args.get('q', '').replace(' ', '_').lower()
        if not py_name:
            return ''
        return all_variables[py_name].get('units', '')
    except KeyError:
        return ''
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/kpi_plots', methods=['GET'])
def get_kpi_plots():
    """Generate KPI indicator chart for a KPI group."""
    try:
        kpi_key = request.args.get('q')
        if not kpi_key or kpi_key not in kpis:
            return jsonify({})
        
        res = shared_state['results'].get('variables', {})
        if not res:
            return jsonify({})
        
        fig = go.Figure()
        
        for i, (k, v) in enumerate(kpis[kpi_key].items()):
            real_name = all_variables[k]['real_name']
            value = res.get(real_name, [None])[-1]
            if value is None:
                value = all_variables[k]['default']
            
            init_value = all_variables[k]['default']
            units = all_variables[k]['units']
            
            fig.add_trace(go.Indicator(
                mode='number+delta' if v.get('showDelta') else 'number',
                value=value,
                title={'text': v['label'], 'font': {'size': KPI_TITLE_SIZE}},
                delta={'reference': init_value, 'font': {'size': KPI_VALUE_SIZE}},
                number={'suffix': f' {units}', 'font': {'size': KPI_VALUE_SIZE}},
                domain={'row': i},
                align='center',
            ))
        
        fig.update_layout(
            grid={'rows': len(kpis[kpi_key]), 'columns': 1, 'pattern': 'independent'},
            margin=dict(t=KPI_MARGIN, b=KPI_MARGIN, l=KPI_MARGIN, r=KPI_MARGIN),
        )
        
        return jsonify(json.loads(fig.to_json()))
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def run_model(initial_time, final_time, time_step, inputs):
    """Execute PySD model with given parameters. Returns time series results."""
    overrides = {}
    stateful_overrides = {}
    
    for py_name, value in inputs.items():
        var_type = all_variables[py_name].get('type')
        if var_type == 'Constant':
            overrides[py_name] = value
        elif var_type == 'Stateful':
            stateful_overrides[py_name] = value

    try:
        res = model.run(
            params=overrides,
            initial_condition=(initial_time, stateful_overrides),
            final_time=final_time,
            time_step=time_step
        )
        
        shared_state['results'] = {
            "time": res.index.tolist(),
            "variables": {col: res[col].tolist() for col in res.columns}
        }
        
        return res
        
    except Exception as e:
        print(f"Error in run_model: {e}")
        raise


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Run simulation for multiple scenarios."""
    try:
        data = request.json or {}
        
        initial_time = float(data.get('initialTime', 0))
        final_time = float(data.get('finalTime', 60))
        time_step = float(data.get('timeStep', 1))
        inputs_by_scenario = data.get('inputs', {})
        
        if final_time <= initial_time:
            final_time = initial_time + 1

        results = {}
        for scenario_name, scenario_inputs in inputs_by_scenario.items():
            try:
                res = run_model(initial_time, final_time, time_step, scenario_inputs)
                results[scenario_name] = {
                    "time": res.index.tolist(),
                    "variables": {col: res[col].tolist() for col in res.columns}
                }
            except Exception as e:
                results[scenario_name] = {"error": str(e)}
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def build_parameter_values(min_val, max_val, steps):
    """Generate evenly spaced parameter values."""
    return np.linspace(min_val, max_val, steps).tolist()


def extract_final_value(result_df, variable_name):
    """Extract the final time point value for a variable from results."""
    if variable_name not in result_df.columns:
        return None
    return float(result_df[variable_name].iloc[-1])


def extract_max_value(result_df, variable_name):
    if variable_name not in result_df.columns:
        return None
    return float(result_df[variable_name].max())


def run_sensitivity_parametric(base_inputs, x_param, x_min, x_max, steps, 
                               y_variable, initial_time, final_time, time_step):
    """
    Run parametric sensitivity: sweep X parameter, run N simulations each with different X value.
    Returns two datasets:
    1. time_series: N full simulation results (Y vs time) for each X value
    2. final_values: N final Y values at each X value
    """
    x_values = build_parameter_values(x_min, x_max, steps)
    time_series_results = []
    final_values_results = []
    y_real_name = all_variables[y_variable]['real_name']
 
    for x_val in x_values:
        inputs = base_inputs.copy()
        inputs[x_param] = x_val
 
        try:
            res_df = run_model(initial_time, final_time, time_step, inputs)
            # Time series: all time points for this X value
            time_series_results.append({
                "x_param_value": x_val,
                "time": res_df.index.tolist(),
                "y_values": res_df[y_real_name].tolist()
            })
            
            # Final value: only the last time point
            max_y = extract_max_value(res_df, y_real_name)
            final_values_results.append({
                "x_param_value": x_val,
                "y_final_value": max_y
            })
        except Exception as e:
            print(f"Error in parametric run with {x_param}={x_val}: {e}")
            continue
 
    return {
        "time_series": time_series_results,
        "final_values": final_values_results
    }
 
 
def run_sensitivity_heatmap(base_inputs, x_param, x_min, x_max, y_param, y_min, y_max, 
                            steps, output_variable, initial_time, final_time, time_step):
    """
    Run heatmap sensitivity: sweep two constant parameters in a grid, measure stateful output at final time.
    Returns 2D grid of output values where x and y are constant parameters, z is the stateful variable.
    """
    x_values = build_parameter_values(x_min, x_max, steps)
    y_values = build_parameter_values(y_min, y_max, steps)
    z_values = []
    output_real_name = all_variables[output_variable]['real_name']
 
    for y_val in y_values:
        row = []
        row_rounded = []
        for x_val in x_values:
            inputs = base_inputs.copy()
            inputs[x_param] = x_val
            inputs[y_param] = y_val

            try:
                res_df = run_model(initial_time, final_time, time_step, inputs)
                z_val = extract_final_value(res_df, output_real_name)
                row.append(z_val if z_val is not None else 0)

                res_df = run_model(initial_time, final_time, time_step, inputs)
            except Exception as e:
                print(f"Error in heatmap run with {x_param}={x_val}, {y_param}={y_val}: {e}")
                row.append(0)
        
        z_values.append(row)

    return {
        "x_variable": x_param,
        "y_variable": y_param,
        "z_variable": output_variable,
        "grid": {
            "x_values": x_values,
            "y_values": y_values,
            "z_values": z_values
        },
        "z_values_rounded": [[round(z, 1) for z in r] for r in z_values],
    }


@app.route('/api/sensitivity', methods=['POST'])
def sensitivity_analysis():
    """
    Run sensitivity analysis for parametric or heatmap mode.
    Parametric: returns time_series (N curves) and final_values (1 summary curve).
    Heatmap: returns 2D grid of final values.
    """
    try:
        data = request.json or {}
        
        mode = data.get('mode', 'parametric')
        variables = data.get('variables', {})
        base_inputs = data.get('baseInputs', {})
        
        initial_time = float(data.get('initialTime', 0))
        final_time = float(data.get('finalTime', 60))
        time_step = float(data.get('timeStep', 1))
        
        if final_time <= initial_time:
            final_time = initial_time + 1

        if mode == 'parametric':
            # Extract X parameter and Y variable from variables dict
            var_keys = list(variables.keys())
            x_param = var_keys[0]
            y_variable = var_keys[1] if len(var_keys) > 1 else None
            
            if not x_param or not y_variable:
                return jsonify({"error": "Parametric mode requires X parameter and Y variable"}), 400
            
            x_config = variables[x_param]
            x_min = x_config.get('min', all_variables[x_param]['min'])
            x_max = x_config.get('max', all_variables[x_param]['max'])
            steps = x_config.get('steps', 15)
            
            results = run_sensitivity_parametric(
                base_inputs, x_param, x_min, x_max, steps,
                y_variable, initial_time, final_time, time_step
            )
            
            return jsonify({
                "mode": "parametric",
                "x_variable": x_param,
                "y_variable": y_variable,
                "time_series": results["time_series"],
                "final_values": results["final_values"]
            })

        elif mode == 'heatmap':
            # Extract X and Y parameters (both constant, both swept) and Z variable (stateful output)
            var_keys = list(variables.keys())
            x_param = var_keys[0]
            y_param = var_keys[1] if len(var_keys) > 1 else None
            z_variable = var_keys[2] if len(var_keys) > 2 else None
            
            if not x_param or not y_param or not z_variable:
                return jsonify({"error": "Heatmap mode requires two constant parameters and one stateful output variable"}), 400
            
            x_config = variables[x_param]
            y_config = variables[y_param]
            
            x_min = x_config.get('min', all_variables[x_param]['min'])
            x_max = x_config.get('max', all_variables[x_param]['max'])
            y_min = y_config.get('min', all_variables[y_param]['min'])
            y_max = y_config.get('max', all_variables[y_param]['max'])
            steps = x_config.get('steps', 5)
            
            result = run_sensitivity_heatmap(
                base_inputs, x_param, x_min, x_max,
                y_param, y_min, y_max, steps,
                z_variable, initial_time, final_time, time_step
            )
            
            return jsonify(result)

        else:
            return jsonify({"error": f"Unknown sensitivity mode: {mode}"}), 400

    except Exception as e:
        print(f"Error in sensitivity_analysis: {e}")
        return jsonify({"error": str(e)}), 500
    

if __name__ == '__main__':
    init()
    app.run(port=5000, debug=True)