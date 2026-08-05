import pysd
import pandas as pd
import numpy as np


class SEIQRModelService:
    def __init__(self, model_path: str = "models/SEIQR_linked.py"):
        self.model_path = model_path
        self._model = pysd.load(model_path)
        self.doc = self._model.doc

    def get_doc(self):
        return self.doc

    def get_stocks(self):
        return self.doc['Py Name'].loc[self.doc['Type'] == 'Stateful']


    def get_parameter_schema(self) -> dict:
        """Extracts editable parameters, limits, units, and defaults from model.doc."""
        schema = {}
        
        limits_df = self.doc[
            self.doc['Limits'].apply(lambda x: isinstance(x, (tuple, list)) and not (np.isnan(x[0]) and np.isnan(x[1])))
        ]
        
        for _, row in self.doc.iterrows():
            py_name = row['Py Name']
            # Safely fetch current component default value
            try:
                default_val = float(getattr(self._model.components, py_name)())
            except Exception:
                default_val = float(row['Limits'][0])

            schema[py_name] = {
                "real_name": row['Real Name'],
                "units": row['Units'],
                "min": float(row['Limits'][0]),
                "max": float(row['Limits'][1]),
                "default": default_val
            }

        init_t = int(self._model.components.initial_time())
        final_t = int(self._model.components.final_time())
        t_step = float(self._model.components.time_step())
        init_infected = int(self._model.components.initial_infected())
        init_population = int(self._model.components.initial_population())

        schema["initial_time"] = {
            "real_name": "Initial Time",
            "units": "Days",
            "min": 0,
            "max": final_t,
            "default": init_t
        }
        schema["final_time"] = {
            "real_name": "Final Time",
            "units": "Days",
            "min": init_t,
            "max": None, 
            "default": final_t
        }
        schema["time_step"] = {
            "real_name": "Time Step",
            "units": "Days",
            "min": 0.001,
            "max": float(final_t - init_t),
            "default": t_step
        }
        schema['initial_infected'] = {
            "real_name": "Initial infected",
            "units": "cattle",
            "min": 0,
            "max": init_population,
            "default": init_infected
        }
        schema['initial_population'] = {
            "real_name": "Initial population",
            "units": "cattle",
            "min": init_infected,
            "max": 50000,
            "default": init_population
        }
        
        return schema

    def run_simulation(self, params: dict, initial_time: float, final_time: float, time_step: float, initial_stocks: dict = {}) -> pd.DataFrame:
        """Executes a scenario run given a dictionary of parameters."""
        scenario = self._model.copy()
        
        # Merge time parameters into the scenario payload
        run_params = {**params, "initial_time": initial_time, "final_time": final_time, "time_step": time_step}
        scenario.set_components(run_params)
        
        return scenario.run(initial_condition=(initial_time, initial_stocks), final_time=final_time)

    def format_simulation_for_api(self, df: pd.DataFrame, view_vars: list[str]) -> dict:
        """Converts a simulation DataFrame into a JSON-serializable dictionary standard."""
        subset = df[view_vars].copy()
        subset.index.name = "time"
        return {
            "time": subset.index.tolist(),
            "series": {col: subset[col].tolist() for col in subset.columns}
        }