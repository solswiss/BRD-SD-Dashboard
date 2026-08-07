from flask import Flask, request, g, jsonify
from flask_cors import CORS
import plotly.express as px
import plotly.graph_objects as go
import pysd
import pandas as pd
import json

app = Flask(__name__)
CORS(app)

model = pysd.load('model.py')
doc = model.doc

shared_state = {'results': {'time':{}, 'variables':{}}}
all_variables_df = doc.dropna(subset=['Py Name'])
all_variables = {}
kpis = {}
KPI_TITLE_SIZE = 12
KPI_VALUE_SIZE = 28
KPI_MARGIN = 50


def init():
    for _, row in all_variables_df.iterrows():
        py_name = row['Py Name']
        try:
            default = float(getattr(model.components, py_name)())
        except:
            default = float(row['Limits'][0])

        units = (row['Units'] if row['Units'] != '1/day' else '/day') if pd.notna(row['Units']) else "UNDEF"

        min = float(row['Limits'][0])
        max = float(row['Limits'][1])
        if not pd.notna(min): min = 0
        if not pd.notna(max):
            max = default * 2
            if default <= 1:
                max = 1
        
        all_variables[py_name] = {
            "py_name": py_name,
            "real_name": row['Real Name'],
            "type": row['Type'],
            "units": units,
            "min": min,
            "max": max,
            "step": 0.05 if default <= 1 else .1,
            "default": default
        }

    with open('kpis.json', 'r') as file:
        data: dict = json.load(file)
        for k,v in data.items():
            vars = {}
            for var, params in v.items():
                vars[var] = params
            kpis[k] = vars

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    try:
        # PySD components directly expose getter evaluation methods for calculations
        controls = {
            "initial_time": float(model.components.initial_time()),
            "final_time": float(model.components.final_time()),
            "time_step": float(model.components.time_step())
        }
        auxiliaries = constants = {}
        for k, v in all_variables.items():
            if v['type'] == 'Auxiliary':
                auxiliaries[k] = v
            elif v['type'] == 'Constant':
                constants[k] = v

        return jsonify({
            "controls": controls,
            "auxiliaries": auxiliaries,
            "constants": constants,
            "kpi_groups": kpis.keys()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/baseline_parameters', methods=['GET'])
def get_baseline_parameters():
    try:
        # PySD components directly expose getter evaluation methods for calculations
        controls = {
            "initial_time": float(model.components.initial_time()),
            "final_time": float(model.components.final_time()),
            "time_step": float(model.components.time_step())
        }
        overrides = {}
        for k, v in all_variables.items():
            if v['type'] == 'Constant':
                overrides[k] = v['default']

        return jsonify({
            "controls": controls,
            "inputs": overrides,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/globals', methods=['GET'])
def get_globals():
    with open('globals.json', 'r') as file:
        data = json.load(file)
        globals = {}
        for variable in data["variables"]:
            globals[variable] = all_variables[variable] # expects py_name
        return jsonify({
            'globals': globals,
            'kpi_groups': [key for key in kpis.keys()]
        })

@app.route('/api/domains', methods=['GET'])
def get_domains():
    with open('domains.json', 'r') as file:
        data = json.load(file)
        constants = {}
        for k, v in all_variables.items():
            if v["type"] == 'Constant':
                constants[k] = v

        domains = {}
        for domain, variables in data.items():
            domains[domain] = [constants[variable] for variable in variables if variable in constants]
        return domains

def get_real_name(pyname:str):
    var = all_variables[pyname]
    if not var: raise Exception(f'{str} is not a valid variable')
    return var['real_name']

@app.route('/api/kpi_plots', methods=['GET'])
def get_kpi_plots():
    kpi_key = request.args.get('q')
    res = shared_state['results']
    if not res or not kpi_key: return {}
    res = res['variables']
    fig = go.Figure()
    for i, [k,v] in enumerate(kpis[kpi_key].items()):
        value = res[get_real_name(k)][-1] or all_variables[k]['default']
        init_value = all_variables[k]['default']
        # threshold = vy['threshold']
        # if threshold and (not threshold[0] or not threshold[1]):
        #     threshold = None
        fig.add_trace(go.Indicator(
            mode = 'number+delta' if v['showDelta'] else 'number',
            value = value,
            title = {'text':v['label'], 'font':{'size':KPI_TITLE_SIZE}},
            delta = {'reference':init_value, 'font':{'size':KPI_VALUE_SIZE}},
            number = {'suffix':' '+all_variables[k]['units'], 'font':{'size':KPI_VALUE_SIZE}},
            domain = {'row':i},
            align='center',
            #gauge = {'axis': {'range': [threshold[0], threshold[1]]}} if threshold else None
        ))
    fig.update_layout(
        grid={'rows':4,'columns':1,'pattern':'independent'},
        margin=dict(t=KPI_MARGIN,b=KPI_MARGIN,l=KPI_MARGIN,r=KPI_MARGIN),
    )
    graph_json = json.loads(fig.to_json())
    return jsonify(graph_json)
    """
      const layout = {
        margin: { l: 12, r: 12, t: 0, b: 0 },
        responsive: true
      }
      Plotly.newPlot(KpiContainers[i], [indicator], layout, { responsive: true })
      """

@app.route('/api/units', methods=['GET'])
def get_units():
    py_name = request.args.get('q')
    if py_name is None: return ''
    return all_variables[py_name.replace(' ','_').lower()].get('units')

def run_model(initial_time, final_time, time_step, inputs):
    overrides = {}
    stateful_overrides = {}
    for pyname, value in inputs.items():
        type = all_variables[pyname].get('type')
        if type == 'Constant':
            overrides[pyname] = value
        elif type == 'Stateful':
            stateful_overrides[pyname] = value

    try:
        res = model.run(
            params=overrides,
            initial_condition=(initial_time, stateful_overrides),
            final_time=final_time,
            time_step=time_step
            )
        
        shared_state['results'] = payload = {
            "time": res.index.tolist(),
            "variables": {col: res[col].tolist() for col in res.columns}
        }
        return payload
        
    except Exception as e:
        print("Exception while in run_model:",e)
        return {}

@app.route('/api/simulate', methods=['POST'])
def simulate():
    data = request.json or {}
    
    # extract controls
    initial_time = float(data.get('initialTime', 0))
    final_time = float(data.get('finalTime', 60))
    time_step = float(data.get('timeStep', 1))
    inputs = data.get('inputs', {})

    # hard guards
    if final_time <= initial_time:
        final_time = initial_time + 1

    try:
        res = {}
        for k,v in inputs.items():
            res[k] = run_model(initial_time, final_time, time_step, v)
        return jsonify(res)
    except Exception as e:
        return jsonify({"Exception in simulate": str(e)}), 400

if __name__ == '__main__':
    init()
    app.run(port=5000, debug=True)
