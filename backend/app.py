from flask import Flask, request, jsonify
from flask_cors import CORS
import plotly.graph_objects as go
import pysd
import pandas as pd
import json

app = Flask(__name__)
CORS(app)

# Load model
model = pysd.load('model.py')
doc = model.doc

# Constants
KPI_TITLE_FONT_SIZE = 12
KPI_VALUE_FONT_SIZE = 28
KPI_MARGIN = 50
DEFAULT_MAX_MULTIPLIER = 2
DEFAULT_MAX_IF_SMALL = 1

# Caches
all_variables = {}
kpis = {}
shared_state = {'results': {'time': {}, 'variables': {}}}


def _build_variable_metadata():
    """Build all_variables dict with normalized data."""
    all_variables_df = doc.dropna(subset=['Py Name'])
    
    for _, row in all_variables_df.iterrows():
        py_name = row['Py Name']
        
        # Get default value
        try:
            default = float(getattr(model.components, py_name)())
        except:
            default = float(row['Limits'][0])
        
        # Normalize units
        units = row['Units'] if pd.notna(row['Units']) else "UNDEF"
        if units == '1/day':
            units = '/day'
        
        # Calculate bounds
        min_val = float(row['Limits'][0]) if pd.notna(row['Limits'][0]) else 0
        max_val = float(row['Limits'][1]) if pd.notna(row['Limits'][1]) else (
            default * DEFAULT_MAX_MULTIPLIER if default > 1 else DEFAULT_MAX_IF_SMALL
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


def _load_kpis():
    """Load KPI configuration from file."""
    with open('kpis.json', 'r') as file:
        data = json.load(file)
        for k, v in data.items():
            kpis[k] = v


def _get_variable(py_name):
    """Get variable metadata by py_name. Raises KeyError if not found."""
    return all_variables[py_name]


def _get_real_name(py_name):
    """Get the real name for a py_name variable."""
    return _get_variable(py_name)['real_name']


def _categorize_variables():
    """Categorize variables by type."""
    controls = {
        "initial_time": float(model.components.initial_time()),
        "final_time": float(model.components.final_time()),
        "time_step": float(model.components.time_step())
    }
    auxiliaries = {}
    constants = {}
    
    for k, v in all_variables.items():
        if v['type'] == 'Auxiliary':
            auxiliaries[k] = v
        elif v['type'] == 'Constant':
            constants[k] = v
    
    return controls, auxiliaries, constants


def _validate_time_bounds(initial_time, final_time):
    """Ensure final_time > initial_time."""
    if final_time <= initial_time:
        return initial_time + 1
    return final_time


def _run_model(initial_time, final_time, time_step, inputs):
    """Execute PySD model with given parameters."""
    overrides = {}
    stateful_overrides = {}
    
    for py_name, value in inputs.items():
        var_type = _get_variable(py_name).get('type')
        if var_type == 'Constant':
            overrides[py_name] = value
        elif var_type == 'Stateful':
            stateful_overrides[py_name] = value
        # not working with Auxiliaries (yet?)

    try:
        res = model.run(
            params=overrides,
            initial_condition=(initial_time, stateful_overrides),
            final_time=final_time,
            time_step=time_step
        )
        
        payload = {
            "time": res.index.tolist(),
            "variables": {col: res[col].tolist() for col in res.columns}
        }
        shared_state['results'] = payload
        return payload
        
    except Exception as e:
        print(f"Error in _run_model: {e}")
        raise


@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Return model structure: controls, auxiliaries, constants, and KPI groups."""
    try:
        controls, auxiliaries, constants = _categorize_variables()
        return jsonify({
            "controls": controls,
            "auxiliaries": auxiliaries,
            "constants": constants,
            "kpi_groups": list(kpis.keys())
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/baseline_parameters', methods=['GET'])
def get_baseline_parameters():
    """Return default control and constant values."""
    try:
        controls, _, _ = _categorize_variables()
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
        
        globals_vars = {var: _get_variable(var) for var in data["variables"]}
        
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
        return _get_variable(py_name).get('units', '')
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
            value = res.get(_get_real_name(k), [None])[-1]
            if value is None:
                value = _get_variable(k)['default']
            
            init_value = _get_variable(k)['default']
            units = _get_variable(k)['units']
            
            fig.add_trace(go.Indicator(
                mode='number+delta' if v.get('showDelta') else 'number',
                value=value,
                title={'text': v['label'], 'font': {'size': KPI_TITLE_FONT_SIZE}},
                delta={'reference': init_value, 'font': {'size': KPI_VALUE_FONT_SIZE}},
                number={'suffix': f' {units}', 'font': {'size': KPI_VALUE_FONT_SIZE}},
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


@app.route('/api/simulate', methods=['POST'])
def simulate():
    """Run simulation for multiple scenarios."""
    try:
        data = request.json or {}
        
        initial_time = float(data.get('initialTime', 0))
        final_time = float(data.get('finalTime', 60))
        time_step = float(data.get('timeStep', 1))
        inputs_by_scenario = data.get('inputs', {})
        
        final_time = _validate_time_bounds(initial_time, final_time)
        
        results = {}
        for scenario_name, scenario_inputs in inputs_by_scenario.items():
            try:
                results[scenario_name] = _run_model(
                    initial_time, final_time, time_step, scenario_inputs
                )
            except Exception as e:
                results[scenario_name] = {"error": str(e)}
        
        return jsonify(results)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400


def init():
    """Initialize app: load variables and KPIs."""
    _build_variable_metadata()
    _load_kpis()


if __name__ == '__main__':
    init()
    app.run(port=5000, debug=True)