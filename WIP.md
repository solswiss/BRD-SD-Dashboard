# Work In Progress: SEIQR_linked
These are testing grounds! End goal is (learn how to develop) a functional HTML dashboard for the model. Everything tested here is a step toward developing an HTML dashboard (drawing inspiration from [En-ROADS](https://en-roads.climateinteractive.org/scenario.html?v=26.7.0)) for the final model(s).  

## Run the dashboard
### Backend tasks
0. CD into `backend`
```
cd backend
```
1. Install required packages
```
pip install requirements.txt
```
2. Start the server
```
python app.py
```
### Frontend tasks
0. CD into `frontend`
```
cd frontend
```
1. Install required packages
```
npm install
```
2. Start the client
```
npm run dev
```
3. Open the dashboard: `ctrl-click` the link or go to `http://localhost:5173`

## TODO
### Current Task Overview
Complete core functionality tasks.

### 1. Core Functionality
- [x] Save/load scenarios
- [x] Globals
- [x] Graph view selection
- [x] KPIs
- [ ] Sensitivity Analysis
- [ ] Scenario Testing
    - [x] disable delete baseline scenario, used as defaults
    - [ ] warn delete

### 2. Frontend
- [ ] Harmonize UI language
- [ ] Consolidate repeating styles, e.g. font sizes (16px) and colors
- [ ] Causal input nesting

### 3. Testing & QA
- [ ] Test inputs
    - [ ] Why is antimicrobial use disproportionately large?
- [ ] Verify cross-browser/device compatibility

### 4. Technical Polish
- [ ] Implement caches
- [ ] Restructure and spread code
- [ ] Enforce types and other checks
- [ ] Verbose error handling
- [ ] Add comments
- [ ] Tidy up code

### 5. Production Readiness
- [ ] Write README.md for user setup and custom config

## Technical Notes
Nothing for now.

## Other Notes
Sourced `colors.json` scheme from [sashamaps](https://sashamaps.net/docs/resources/20-colors/)

## Discussion
### Blockers
- [ ] (minor) Missing descriptions for input
    - [ ] Check existing descriptions (Comment)
### Questions
Nothing for now.