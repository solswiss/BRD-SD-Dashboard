# System Dynamics Modeling Dashboard
Dashboard prototype developed for research on System Dynamics Modeling of Bovine Respiratory Disease conducted in the Artificial Intelligence for Sustainable Livestock Systems Lab at Texas A&amp;M University, College Station, Texas.

## Map
To compare scenarios and run sensitivity tests, go to the Lab page, which is accessible through a button in the upper right corner  
Left sidebar holds view settings (e.g. chart, (input) domain, KPIs) and scenario controls (e.g. create, load, delete)  
Center display holds a chart that plots all the active/selected scenarios, which can be changed from the sidebar  
Right display holds the KPIs, which can be changed from the sidebar  
Inputs section holds all the constant inputs, separated by domain
To isolate inputs for one domain, change `Domain` from the sidebar or click the domain name within the inputs section  

## User Instructions
### Installation & Running
Complete the backend tasks before moving on to the frontend tasks. If you're unfamiliar with terminal commands, the directory instructions (e.g. `cd backend`) should be done from the root folder; you can open separate terminals or do `cd ..` to go back one folder. It's recommended that you create a virtual environment for the Python packages.
#### Backend tasks
1. Install the required packages for backend processes. Also optionally create and activate virtual environment (venv) for package installations prior to this step.
```
cd backend
pip install -r requirements.txt
```
2. Start the server. Ensure that the Flask server started successfully (e.g. terminal confirmation: `Running on http://127.0.0.1:5000`) before continuing.
```
python app.py
```

#### Frontend tasks
1. Install the required packages for backend processes.
```
cd frontend
npm install
```
2. Start the client
```
npm run dev
```
3. Open the dashboard: `ctrl-click` the link or go to `http://localhost:5173`

### Setup
There is limited support for customization (see the hard-coded logo, for example, which may be addressed soon) but setting up a new model is very doable. If you have a PYSD model file, go to step 3.
1. Add a `.mdl` file to folder `backend`
2. Run `convert_model.py`
```python convert_model.py```
3. Rename the generated `.py` file to `model.py`
4. Update the `.json` files in folder `setup config`

#### Helpful Tips
- Reference `model.py` for the Python versions of variable names which are lowercase and camelcase (e.g. `Quarantine rate` --> `quarantine_rate`)
- If a JSON file has an error, see if it uses the python or real variable name instead, if the format is incorrect, if you forgot to close a string (or brace!)
- `charts.json` defines charts with a chart title (`"Antimicrobial Use"`) and uses real variable names as each trace (`"Metaphylactic usage"`)
- `colors.json` defines a color `"scheme"` with an array of colors as strings (`"#f00"`) which are used as trace colors
- `domains.json` defines domains (`"Epidemiological"`) which separate input variables (`"metaphylactic_usage"`)
    - Excessive domains (maybe 5+) will clutter the space
- `globals.json` defines `"variables"` to be easily accessed from the sidebar (`"initial_time"`)
- `kpis.json` defines groups (`"Epidemiology"`) of key performance indicators (KPIs):
    - Each KPI begins with a name (`"force_of_infection"`)
    - `"label"` is what the KPI titled, and can just be its real name (`"Force of Infection"`)
    - `"showDelta"` decides whether or not to show delta for this KPI (`true` or `false`)
- `settings.json` defines a `"title"` and `"footnote"`