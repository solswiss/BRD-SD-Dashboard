import pysd
import streamlit as st
import pandas as pd
import numpy as np


st.title("SEIQR_linked Dashboard")
st.set_page_config(layout='wide')

def reset():
    st.cache_resource.clear()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

@st.cache_resource
def load_model():
    return pysd.load("SEIQR_linked.py")

model = load_model() # the baseline is never modified, though this may be unnecessary
scenario = model.copy()
model_df = model.run()

INITIAL_MODEL_STATE = model.doc
#st.dataframe(INITIAL_MODEL_STATE)
#st.dataframe(INITIAL_MODEL_STATE.loc[INITIAL_MODEL_STATE['Limits'].apply(lambda x: not (np.isnan(x[0]) and np.isnan(x[1]))), ['Py Name','Units','Limits']])

INITIAL_TIME = float(model.components.initial_time())
FINAL_TIME = float(model.components.final_time())
TIME_UNITS = 'Days'
TIME_LABEL = f'Time ({TIME_UNITS})'
MODEL_LIMITS = INITIAL_MODEL_STATE[INITIAL_MODEL_STATE['Limits'].apply(lambda x: not (np.isnan(x[0]) and np.isnan(x[1])))]
MODEL_LIMITS_DICT = dict(zip(MODEL_LIMITS['Py Name'], MODEL_LIMITS['Limits']))
MODEL_ALL_VARS = INITIAL_MODEL_STATE['Real Name'].to_list() #[v.capitalize() for v in INITIAL_MODEL_STATE['Real Name'].to_list()] <-- messes up all-caps e.g. ADG -> Adg

views_vars_dict: dict[str, list[str]] = {
    'SEIQR':['Susceptible','Infected','Quarantine','Exposed','Recovered'],
    'Antimicrobial Use':['Cumulative antimicrobial usage','Metaphylactic usage','Therapeutic usage'],
    'Economic Outcomes':['Profit','Herd Revenue','Total Production Loss','Healthcare cost'],
} | {v:[v] for v in MODEL_ALL_VARS}

#INITIAL_SESSION_STATE = 
# Revenue rate; ; Healthcare cost, Non-Healthcare cost
# Herd Revenue; fractional profitability rate; Production Cost
# Profitability rate

if st.button('Reset'): reset()
def validate_initial_time():
    if st.session_state.initial_time >= st.session_state.final_time:
        st.session_state.initial_time = st.session_state.final_time-1
def validate_final_time():
    if st.session_state.initial_time >= st.session_state.final_time:
        st.session_state.final_time = st.session_state.initial_time+1
a, b, c, d = st.columns(4)
with a:
    initial_time = st.number_input('Initial time',0.0,None,INITIAL_TIME,key='initial_time',on_change=validate_initial_time)
with b:
    final_time = st.number_input('Final time',0.0,None,FINAL_TIME,key='final_time',on_change=validate_final_time)
with c:
    time_step = st.number_input('Time step',0.0,float(final_time),scenario.components.time_step())
with d:
    view = st.selectbox('Graph view',views_vars_dict.keys(),key='view')
# if initial_time >= final_time:
#     print('Initial time must be less than final time & Final time must be greater than initial time')
#     st.initial_time 


display_container = st.container()
with display_container:
    #TODO add axis labels
    #TODO add units for individual lines
    st.subheader(view)
    seiqr_chart = st.empty()
    c1, c2 = st.columns(2)
    with c1:
        #st.markdown("This column has been purposefully left empty.")
        st.subheader('Antimicrobial Use')
        epidemiological_chart = st.empty()
    with c2:
        st.subheader('Economic Outcomes')
        economic_chart = st.empty()

# INPUTS
input_container = st.container()
with input_container:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("Epidemiological")
        x, y = st.columns(2)
        with x:
            pathogen_load = st.slider('Pathogen Load', MODEL_LIMITS_DICT['pathogen_load'][0], MODEL_LIMITS_DICT['pathogen_load'][1], scenario.components.pathogen_load())
            fractional_mortality = st.slider('Fractional Mortality', MODEL_LIMITS_DICT['fractional_mortality'][0], MODEL_LIMITS_DICT['fractional_mortality'][1], scenario.components.fractional_mortality())
            age_score = st.slider('Age Score', MODEL_LIMITS_DICT['age_score'][0], MODEL_LIMITS_DICT['age_score'][1], float(scenario.components.age_score()))
            preconditioning_score = st.slider('Preconditioning Score', MODEL_LIMITS_DICT['preconditioning_score'][0], MODEL_LIMITS_DICT['preconditioning_score'][1], float(scenario.components.preconditioning_score()))
        with y:
            incubation_period = st.slider('Incubation Period', int(MODEL_LIMITS_DICT['incubation_period'][0]), int(MODEL_LIMITS_DICT['incubation_period'][1]), scenario.components.incubation_period())
            average_infection_time = st.slider('Average Infection Time', MODEL_LIMITS_DICT['average_infection_time'][0], MODEL_LIMITS_DICT['average_infection_time'][1], float(scenario.components.average_infection_time()))
            average_time_to_recovery_in_quarantine = st.slider('Average Time To Recovery In Quarantine', MODEL_LIMITS_DICT['average_time_to_recovery_in_quarantine'][0], MODEL_LIMITS_DICT['average_time_to_recovery_in_quarantine'][1], float(scenario.components.average_time_to_recovery_in_quarantine()))
        st.markdown('#### Metaphylaxis')
        x, y = st.columns(2)
        with x:
            metaphylaxis_dosage = st.slider('Metaphylaxis dosage',MODEL_LIMITS_DICT['metaphylaxis_dosage'][0],MODEL_LIMITS_DICT['metaphylaxis_dosage'][1],scenario.components.metaphylaxis_dosage())
        with y:
            usage_frequency_m = st.slider('Metaphylaxis usage frequency',int(MODEL_LIMITS_DICT['usage_frequency_m'][0]),int(MODEL_LIMITS_DICT['usage_frequency_m'][1]),scenario.components.usage_frequency_m())
        st.markdown('#### Therapeutic')
        x, y = st.columns(2)
        with x:
            treatment_dosage = st.slider('Therapeutic treatment dosage',MODEL_LIMITS_DICT['treatment_dosage'][0],MODEL_LIMITS_DICT['treatment_dosage'][1],scenario.components.treatment_dosage())
        with y:
            usage_frequency_t = st.slider('Therapeutic usage frequency',int(MODEL_LIMITS_DICT['usage_frequency_t'][0]),int(MODEL_LIMITS_DICT['usage_frequency_t'][1]),scenario.components.usage_frequency_t())
    with c2:
        st.subheader("Sociodynamic")
        '''contact_rate, vaccination_coverage, transportation_score, commingling_score, average_time_to_quarantine'''
        
        '''season_score, weather_score'''
    with c3:
        st.subheader("Economic")
        x, y = st.columns(2)
        with x:
            unit_nonhealthcare_cost = st.slider('Unit non-healthcare cost',MODEL_LIMITS_DICT['unit_nonhealthcare_cost'][0],MODEL_LIMITS_DICT['unit_nonhealthcare_cost'][1],float(scenario.components.unit_nonhealthcare_cost()))
            fractional_profitability_rate = st.slider('Fractional profitability rate',0.0,5.0,float(scenario.components.fractional_profitability_rate())) #FIXME hardcoded limits
        with y:
            opportunity_cost = st.slider('Opportunity cost',MODEL_LIMITS_DICT['opportunity_cost'][0],MODEL_LIMITS_DICT['opportunity_cost'][1],scenario.components.opportunity_cost())
            adg_reduction_rate = st.slider('ADG reduction rate',MODEL_LIMITS_DICT['adg_reduction_rate'][0],MODEL_LIMITS_DICT['adg_reduction_rate'][1],scenario.components.adg_reduction_rate())
        st.markdown("#### Healthcare")
        x, y = st.columns(2)
        with x:
            vaccination_coverage = st.slider('Vaccination coverage',MODEL_LIMITS_DICT['vaccination_coverage'][0],MODEL_LIMITS_DICT['vaccination_coverage'][1],scenario.components.vaccination_coverage())
            unit_cost_of_vaccine = st.slider('Unit vaccine cost',MODEL_LIMITS_DICT['unit_cost_of_vaccine'][0],MODEL_LIMITS_DICT['unit_cost_of_vaccine'][1],float(scenario.components.unit_cost_of_vaccine()))
        with y:
            unit_cost_of_therapeutic_amu = st.slider('Unit therapeutic AMU cost',MODEL_LIMITS_DICT['unit_cost_of_therapeutic_amu'][0],MODEL_LIMITS_DICT['unit_cost_of_therapeutic_amu'][1],float(scenario.components.unit_cost_of_therapeutic_amu()))
            unit_cost_of_metaphylactic_amu = st.slider('Unit metaphylactic AMU cost',MODEL_LIMITS_DICT['unit_cost_of_metaphylactic_amu'][0],MODEL_LIMITS_DICT['unit_cost_of_metaphylactic_amu'][1],float(scenario.components.unit_cost_of_therapeutic_amu()))

scenario.set_components({
    'initial_time':initial_time,
    'final_time':final_time,
    'time_step':time_step,
    'metaphylaxis_dosage':metaphylaxis_dosage,
    'usage_frequency_m':usage_frequency_m,
    'usage_frequency_t':usage_frequency_t,
    'treatment_dosage':treatment_dosage,
    'vaccination_coverage':vaccination_coverage,
    'pathogen_load':pathogen_load,
    'age_score':age_score,
    'preconditioning_score':preconditioning_score,
    'incubation_period':incubation_period,
    'average_infection_time':average_infection_time,
    'average_time_to_recovery_in_quarantine':average_time_to_recovery_in_quarantine,
    'fractional_mortality':fractional_mortality,
    'unit_cost_of_vaccine':unit_cost_of_vaccine,
    'unit_cost_of_therapeutic_amu':unit_cost_of_therapeutic_amu,
    'unit_cost_of_metaphylactic_amu':unit_cost_of_metaphylactic_amu,
    'unit_nonhealthcare_cost':unit_nonhealthcare_cost,
    'fractional_profitability_rate':fractional_profitability_rate,
    'opportunity_cost':opportunity_cost,
    'adg_reduction_rate':adg_reduction_rate,
})
scenario_df = scenario.run(initial_condition=(initial_time,{}),final_time=final_time)
st.dataframe(scenario_df)
seiqr_chart.line_chart(scenario_df[views_vars_dict[view]],x_label=TIME_LABEL)

epidemiological_chart.line_chart(scenario_df[views_vars_dict['Antimicrobial Use']],x_label=TIME_LABEL)

economic_chart.line_chart(scenario_df[views_vars_dict['Economic Outcomes']],x_label=TIME_LABEL)

#combined_df = pd.concat([model_df, scenario_df], axis=0)
#economic_chart.line_chart(pd.concat([model_df[ECONOMIC_CHART_VARS].add_prefix('Baseline '),scenario_df[ECONOMIC_CHART_VARS].add_prefix('Scenario ')],axis=1))