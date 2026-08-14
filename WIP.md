# Work In Progress: SEIQR_linked
These are testing grounds! End goal is (learn how to develop) a functional HTML dashboard for the model. Everything tested here is a step toward developing an HTML dashboard (drawing inspiration from [En-ROADS](https://en-roads.climateinteractive.org/scenario.html?v=26.7.0)) for the final model(s).  

## TODO
### Current Task Overview
Complete core functionality tasks.

### 1. Core Functionality
- [x] Save/load scenarios
- [x] Globals
- [x] Graph view selection
- [x] KPIs
- [x] Sensitivity Analysis
- [x] Scenario Testing
    - [x] disable delete baseline scenario, used as defaults

### 2. Frontend
- [x] Harmonize UI language
- [x] Sensitivity plots colors
- [ ] Consolidate repeating styles, e.g. font sizes (16px) and colors
- [ ] Causal input nesting
- [ ] ! Toast notifications
- [x] Check against empty scenario name inputs
- [x] Loading page
    - [x] Error text if backend connection fails
- [ ] Change input mode for sensitivity testing mode (should not be toggle group)
- [ ] Sensitivity plots to accept up to n variables
- [ ] Fix width changes on `Select` trigger
- [ ] Adapt to addl screen sizes

### 3. Testing & QA
- [x] Test inputs
    1. Q: Why is antimicrobial use disproportionately large? A: Because the equation for cumulative antimicrobial use is INTEG of two stocks as opposed to two rates.
- [ ] Verify cross-browser/device compatibility
- [ ] Add safety checks for faulty imports etc.
- [ ] Variable dependencies validation/warnings: sensitivity analysis
- [x] ! Plots subtly fail on occasion and for unknown reasons, but can be fixed by restarting the server—may be related to server caching
    - If you notice this happening (e.g. inputs not updating the plot (if expected), variable ranges (in `Lab`) result in the same dependent values (if the values should differ)) please note it and your interactions with the dashboard before and afterward and open an issue or contact me.
    - The problem was that the model does not like when some variables are zero (e.g. divide by zero error), and I've implemented large safety nets which mute the errors (will show up as toast notifications) and do not update charts with misleading plots.

### 4. Technical Polish
- [ ] UX functions
    - [ ] Rename scenario
    - [ ] Warn scenario delete
    - [ ] Scenario input code injection guards
- [ ] KPI versatility: use donut plots, accept thresholds
- [ ] Implement caches
- [ ] Restructure and spread code
- [ ] Enforce types and other checks
- [ ] Verbose error handling
- [ ] Add comments
- [ ] Tidy up code

### 5. Production Readiness
- [ ] Settings:
    - [ ] Logo: link or local SVG?
- [ ] Safety checks against empty or malformed config imports
- [ ] Write README.md for user setup and custom config

## Technical Notes
Switched out the global variable `init s` for `initial population` and `initial infected`
- `init s` is an auxiliary variable and equivalent to `initial population - initial infected` therefore the switch is adequate
Hacky workaround for `InputField` due to the Svelte 4 nature of Carbon Components
- Easy fix: using vanilla `range` or a Svelte 5 component
Litany of `derived_inert` warnings (from Svelte), may require package updates to fix
Main display (simulation) has a skeleton loader; scenario and sensitivity displays do not
- Q: Should they?
`conversion_helpers.py` is just for developing convenience and can be safely deleted.
## Other Notes
Components from shadcn-svelte and Carbon Svelte
`MultiSelect` from [svelte-multiselect](https://www.npmjs.com/package/svelte-multiselect)
Useful color resource: https://leonardocolor.io/scales.html

## Discussion
### Blockers
- [ ] (minor) Missing descriptions for input

### Questions
Nothing for now.