import streamlit as st
from models import SEIQRModelService
from graph_config import build_view_options
import scipy.interpolate as interpolate


# Group mappings map UI sections to parameter 'Py Name' keys
PARAMETER_GROUPS = {
    "Epidemiological": {
        0: {
            'values': ['pathogen_load', 'vaccination_coverage', 'fractional_mortality', 'incubation_period', 
            'average_infection_time', 'average_time_to_recovery_in_quarantine']
        },
        1: {
            'name': 'Metaphylaxis & Therapeutic',
            'values': [
            'metaphylaxis_dosage', 'usage_frequency_m', 
            'treatment_dosage', 'usage_frequency_t'
            ]
        },
    },
    "Sociodynamic": {
        0: {
            'values': ['initial_infected', 'initial_population', 'contact_rate', 'average_time_to_quarantine']
        },
        1: {
            'name': "Risk Factor Score",
            'values': ['transportation_score', 'commingling_score', 'age_score', 'preconditioning_score', 'season_score', 'weather_score']
        }
    },
    "Economic": {
        0: {
            'values': ['unit_nonhealthcare_cost', 'opportunity_cost', 'adg_reduction_rate', 'steerheifer_value'] # removed 'fractional_profitability_rate'
        },
        1: {
            'name': "Healthcare",
            'values': [
                'unit_cost_of_vaccine', 
                'unit_cost_of_therapeutic_amu', 'unit_cost_of_metaphylactic_amu'
            ],
        },
    }
}


def render_sliders(schema: dict, group_keys: list[str], columns: bool = False) -> dict:
    """Renders sliders dynamically based on schema metadata and returns updated parameters.
    
    Args:
        schema (dict): Parameter schema containing min, max, units, real_name, and default.
        group_keys (list[str]): List of schema keys to render in this section.
        columns (bool): If True, splits inputs into 2 equal Streamlit columns.
    """
    user_inputs = {}
    
    # Filter out keys that don't exist in the schema
    valid_keys = [k for k in group_keys if k in schema]
    
    if not valid_keys:
        return user_inputs

    # Setup layout containers based on columns boolean
    if columns:
        col1, col2 = st.columns(2)
        cols = [col1, col2]
    
    for idx, key in enumerate(valid_keys):
        meta = schema[key]
        
        # Target alternating columns if enabled, otherwise render in current container
        target_container = cols[idx % 2] if columns else st

        # Determine step size and type based on integer vs float bounds
        is_int = isinstance(meta['min'], int) and isinstance(meta['max'], int)
        step = 1 if is_int else 0.01

        # Format label cleanly with units if present
        label = f"{meta['real_name']} ({meta['units']})" if meta.get('units') else meta['real_name']

        user_inputs[key] = target_container.slider(
            label=label,
            min_value=meta['min'],
            max_value=meta['max'],
            value=meta['default'],
            step=step,
            key=f"input_{key}"
        )

    return user_inputs

def render_number_inputs(schema: dict, group_keys: list[str], columns: bool = False) -> dict:
    """Renders number input widgets dynamically based on schema metadata and returns updated parameters.
    
    Args:
        schema (dict): Parameter schema containing min, max, units, real_name, and default.
        group_keys (list[str]): List of schema keys to render in this section.
        columns (bool): If True, splits inputs into 2 equal Streamlit columns.
    """
    user_inputs = {}
    
    # Filter out keys that don't exist in the schema
    valid_keys = [k for k in group_keys if k in schema]
    
    if not valid_keys:
        return user_inputs

    # Setup layout containers based on columns boolean
    if columns:
        col1, col2 = st.columns(2)
        cols = [col1, col2]
    
    for idx, key in enumerate(valid_keys):
        meta = schema[key]
        
        # Target alternating columns if enabled, otherwise render in current container
        target_container = cols[idx % 2] if columns else st

        # Determine step size and type based on integer vs float bounds
        is_int = isinstance(meta['min'], int) and isinstance(meta['max'], int)
        step = 1 if is_int else 0.01

        # Format label cleanly with units if present
        label = f"{meta['real_name']} ({meta['units']})" if meta.get('units') else meta['real_name']

        user_inputs[key] = target_container.number_input(
            label=label,
            value=meta['default'],
            key=f"input_{key}"
        )

    return user_inputs

def make_pulse_override(default_val: float, target_val: float, start_time: float, stop_time: float):
    """Returns a step-up/step-down pulse function over time."""
    def pulse_param(t):
        if start_time <= t <= stop_time:
            return target_val
        return default_val
    return pulse_param


st.set_page_config(layout='wide')
st.title("SEIQR_linked Dashboard")


# sector config
header = st.container(key='header')
display = st.container()


# model
@st.cache_resource
def get_service():
    return SEIQRModelService("models/SEIQR_linked.py")

service: SEIQRModelService = get_service()


# data
schema = service.get_parameter_schema()
doc = service.get_doc()
views = build_view_options(schema, doc)
stocks = list(service.get_stocks())


# sidebar
collected_stocks = {}
def validate_initial_time():
    if st.session_state.initial_time >= st.session_state.final_time:
        st.session_state.initial_time = st.session_state.final_time-1
def validate_final_time():
    if st.session_state.initial_time >= st.session_state.final_time:
        st.session_state.final_time = st.session_state.initial_time+1
def reset():
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
with st.sidebar:
    st.header('Initial State')    

    st.subheader('Controls')
    view = st.selectbox('Graph view',views.keys(),key='view')
    a, b, c = st.columns(3)
    with a:
        initial_time = st.number_input('Initial time',0,None,schema['initial_time'].get('default'),key='initial_time',on_change=validate_initial_time)
    with b:
        final_time = st.number_input('Final time',0,None,schema['final_time'].get('default'),key='final_time',on_change=validate_final_time)
    with c:
        time_step = st.number_input('Time step',0.0,float(final_time),schema['time_step'].get('default'))
    if st.button('Reset'): reset()

    st.subheader('Stocks')
    collected_stocks.update(render_number_inputs(schema, stocks, True))


# parameter gathering
collected_params = {}

c1, c2, c3 = st.columns(3)
with c1:
    x = st.container()
    y = st.container()
    with x:
        st.markdown("### Epidemiological")
        collected_params.update(render_sliders(schema, PARAMETER_GROUPS["Epidemiological"][0].get('values'),True))
    with y:
        group = PARAMETER_GROUPS["Epidemiological"][1]
        st.markdown(f"#### {group.get('name')}")
        collected_params.update(render_sliders(schema, group.get('values'),True))
with c2:
    x = st.container()
    y = st.container()
    with x:
        st.markdown("### Sociodynamic")
        collected_params.update(render_sliders(schema, PARAMETER_GROUPS["Sociodynamic"][0].get('values'),True))
    with y:
        group = PARAMETER_GROUPS["Sociodynamic"][1]
        st.markdown(f"#### {group.get('name')}")
        collected_params.update(render_sliders(schema, group.get('values'),True))
with c3:
    x = st.container()
    y = st.container()
    with x:
        st.markdown("### Economic")
        collected_params.update(render_sliders(schema, PARAMETER_GROUPS["Economic"][0].get('values'),True))
    with y:
        group = PARAMETER_GROUPS["Economic"][1]
        st.markdown(f"#### {group.get('name')}")
        collected_params.update(render_sliders(schema, group.get('values'),True))


# Run Simulation
results_df = service.run_simulation(collected_params, initial_time, final_time, time_step, initial_stocks=collected_stocks)


# Display
with display:
    st.subheader(f"{view}")

    c1, c2 = st.columns([.7, .3])
    with c1: st.line_chart(results_df[views[view]])
    with c2:
        # KPI
        dfi = results_df['current population']
        final_value = dfi.iloc[-1]
        initial_value = dfi.iloc[0]
        delta = dfi.diff()
        pct_change = dfi.pct_change()

        st.metric(f'Cattle population by day {final_time}', int(final_value), int(final_value-initial_value), chart_data=dfi, height='stretch', width='stretch', delta_description=f'since day {initial_time}')