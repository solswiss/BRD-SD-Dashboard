# Work In Progress: SEIQR_linked
These are testing grounds! End goal is (learn how to develop) a functional HTML dashboard for the model. Everything tested here is a step toward developing an HTML dashboard (drawing inspiration from [En-ROADS](https://en-roads.climateinteractive.org/scenario.html?v=26.7.0)) for the final model(s).  

## Run the dashboard
1. Install required packages
```
pip install requirements.txt
```
2. Run the Streamlit app
```
streamlit run SEIQR_linked_streamlit.py
```

## TODO
### Current Task Overview
Review units and input aggregation. Implement most important functionality in Streamlit and migrate to HTML. 

### 1. Core Functionality
- [x] Link constant inputs to graphs
- [x] Graph selection
- [x] Build useful dict
- [ ] Save/load models
- [ ] [Add necessary features](##Discussion)
- [x] Add initial state controls
- [x] Work on `TODO` comments

### 2. Frontend
- [ ] Harmonize UI language
- [ ] Determine graph scales

### 3. Testing & QA
- [ ] Test inputs
- [ ] Verify cross-browser/device compatibility

## Technical Notes
Nothing for now.

## Discussion
### Blockers
- [ ] Waiting on feedback
- [ ] (minor) Missing descriptions for input
### Questions
- [ ] Which inputs are expected and at what level of aggregation and or in which, if any, groups?
- [ ] Should lines scale relative to itself or the largest scale i.e. graph?
- [ ] Additions to necessary features?