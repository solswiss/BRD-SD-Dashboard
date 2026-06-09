"""
Python model 'SEIQR_risk.py'
Translated using PySD
"""

from pathlib import Path
import numpy as np

from pysd.py_backend.statefuls import Integ
from pysd import Component

__pysd_version__ = "3.14.3"

__data = {"scope": None, "time": lambda: 0}

_root = Path(__file__).parent


component = Component()

#######################################################################
#                          CONTROL VARIABLES                          #
#######################################################################

_control_vars = {
    "initial_time": lambda: 0,
    "final_time": lambda: 365,
    "time_step": lambda: 0.125,
    "saveper": lambda: time_step(),
}


def _init_outer_references(data):
    for key in data:
        __data[key] = data[key]


@component.add(name="Time")
def time():
    """
    Current time of the model.
    """
    return __data["time"]()


@component.add(
    name="FINAL TIME", units="day", comp_type="Constant", comp_subtype="Normal"
)
def final_time():
    """
    The final time for the simulation.
    """
    return __data["time"].final_time()


@component.add(
    name="INITIAL TIME", units="day", comp_type="Constant", comp_subtype="Normal"
)
def initial_time():
    """
    The initial time for the simulation.
    """
    return __data["time"].initial_time()


@component.add(
    name="SAVEPER",
    units="day",
    limits=(0.0, np.nan),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"time_step": 1},
)
def saveper():
    """
    The frequency with which output is stored.
    """
    return __data["time"].saveper()


@component.add(
    name="TIME STEP",
    units="day",
    limits=(0.0, np.nan),
    comp_type="Constant",
    comp_subtype="Normal",
)
def time_step():
    """
    The time step for the simulation.
    """
    return __data["time"].time_step()


#######################################################################
#                           MODEL VARIABLES                           #
#######################################################################


@component.add(
    name="Susceptibility Rate",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"recovered": 1, "immunity_loss": 1},
)
def susceptibility_rate():
    return recovered() / immunity_loss()


@component.add(
    name="Susceptible",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_susceptible": 1},
    other_deps={
        "_integ_susceptible": {
            "initial": {"init_s": 1},
            "step": {"susceptibility_rate": 1, "exposure_rate": 1},
        }
    },
)
def susceptible():
    return _integ_susceptible()


_integ_susceptible = Integ(
    lambda: susceptibility_rate() - exposure_rate(),
    lambda: init_s(),
    "_integ_susceptible",
)


@component.add(name="Immunity Loss", comp_type="Constant", comp_subtype="Normal")
def immunity_loss():
    return 1


@component.add(
    name="inital stress",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def inital_stress():
    return 0.025


@component.add(
    name="preconditioning effect",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"preconditioning_score": 1},
)
def preconditioning_effect():
    return 1 / (1 + 1.5 * preconditioning_score())


@component.add(
    name="Stress Buildup",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "age_score": 1,
        "commingling_effect": 1,
        "preconditioning_effect": 1,
        "season_stress": 1,
        "transportation_stress": 1,
        "weather_stress": 1,
    },
)
def stress_buildup():
    return (
        age_score()
        + commingling_effect()
        + (1 - preconditioning_effect())
        + season_stress()
        + transportation_stress()
        + weather_stress()
    ) / 6


@component.add(
    name="BRD Stress",
    units="Dmnl",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_brd_stress": 1},
    other_deps={
        "_integ_brd_stress": {
            "initial": {"inital_stress": 1},
            "step": {"stress_buildup": 1, "stress_recovery": 1},
        }
    },
)
def brd_stress():
    return _integ_brd_stress()


_integ_brd_stress = Integ(
    lambda: stress_buildup() - stress_recovery(),
    lambda: inital_stress(),
    "_integ_brd_stress",
)


@component.add(
    name="transportation stress",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"average_transit_time_hours": 1, "average_transport_distance_miles": 1},
)
def transportation_stress():
    return 0.5 * (
        1 / (1 + float(np.exp(-0.2 * (average_transit_time_hours() - 6))))
    ) + 0.5 * (1 - float(np.exp(-average_transport_distance_miles() / 400)))


@component.add(
    name="commingling effect",
    units="Dmnl",
    limits=(0.001, 1.0, 0.001),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"contact_rate": 1},
)
def commingling_effect():
    return 1 - float(np.exp(-0.15 * contact_rate()))


@component.add(
    name="Stress Recovery",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"brd_stress": 1, "stress_adaptation_time": 1},
)
def stress_recovery():
    return brd_stress() / stress_adaptation_time()


@component.add(
    name="stress adaptation time",
    units="Dmnl",
    limits=(0.0, 20.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def stress_adaptation_time():
    return 2


@component.add(
    name="transmission probability",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"brd_stress": 1, "vaccination_coverage": 1, "infectivity": 1},
)
def transmission_probability():
    return brd_stress() * (1 - vaccination_coverage()) * infectivity()


@component.add(
    name="preconditioning score",
    units="Dmnl",
    limits=(0.01, 1.0, 0.01),
    comp_type="Constant",
    comp_subtype="Normal",
)
def preconditioning_score():
    return 1


@component.add(
    name="age score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"average_age_months": 1},
)
def age_score():
    return 0.8 * float(np.exp(-0.08 * average_age_months())) + 0.2


@component.add(
    name='"average age (months)"',
    units="Dmnl",
    limits=(5.0, 12.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_age_months():
    return 10


@component.add(
    name='"average ambient temperature (F)"',
    units="Dmnl",
    limits=(-10.0, 120.0, 5.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_ambient_temperature_f():
    return 70


@component.add(
    name='"average humidity (%)"',
    units="Dmnl",
    limits=(35.0, 90.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_humidity_():
    return 45


@component.add(
    name='"season (0:winter, 1:spring, 2:summer, 3: fall)"',
    units="Dmnl",
    limits=(0.0, 4.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def season_0winter_1spring_2summer_3_fall():
    return 2


@component.add(
    name='"average transit time (hours)"',
    units="Dmnl",
    limits=(2.0, 24.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_transit_time_hours():
    return 5


@component.add(
    name='"average transport distance (miles)"',
    units="Dmnl",
    limits=(50.0, 1000.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_transport_distance_miles():
    return 250


@component.add(
    name="season stress",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"season_0winter_1spring_2summer_3_fall": 1},
)
def season_stress():
    return 0.6 + 0.3 * float(
        np.cos(2 * 3.14159 * (season_0winter_1spring_2summer_3_fall() - 3) / 4)
    )


@component.add(
    name="weather stress",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"average_ambient_temperature_f": 1, "average_humidity_": 1},
)
def weather_stress():
    return 0.5 * (float(np.abs(average_ambient_temperature_f() - 65)) / 40) + 0.5 * (
        average_humidity_() / 100
    )


@component.add(
    name="Infected mortality rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"infected": 1, "fractional_mortality": 1},
)
def infected_mortality_rate():
    return infected() * fractional_mortality()


@component.add(
    name="fractional mortality",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def fractional_mortality():
    return 0.05


@component.add(
    name="Force of infection",
    units="1/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "contact_rate": 1,
        "transmission_probability": 1,
        "current_population": 1,
        "infected": 1,
    },
)
def force_of_infection():
    return (
        contact_rate()
        * transmission_probability()
        * (infected() / current_population())
    )


@component.add(
    name="Exposure Rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"susceptible": 1, "force_of_infection": 1},
)
def exposure_rate():
    return susceptible() * force_of_infection()


@component.add(
    name="infectivity",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"pathogen_load": 1},
)
def infectivity():
    return pathogen_load()


@component.add(
    name="current population",
    units="cattle",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "exposed": 1,
        "quarantine": 1,
        "recovered": 1,
        "susceptible": 1,
        "infected": 1,
    },
)
def current_population():
    return exposed() + quarantine() + recovered() + susceptible() + infected()


@component.add(
    name="Infection Rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"incubation_period": 1, "exposed": 1},
)
def infection_rate():
    return (1 / incubation_period()) * exposed()


@component.add(
    name="Total Deaths",
    units="cattle",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"infected_mortality": 1, "quarantine_deaths": 1},
)
def total_deaths():
    return infected_mortality() + quarantine_deaths()


@component.add(
    name="Infected Mortality",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_infected_mortality": 1},
    other_deps={
        "_integ_infected_mortality": {
            "initial": {},
            "step": {"infected_mortality_rate": 1},
        }
    },
)
def infected_mortality():
    return _integ_infected_mortality()


_integ_infected_mortality = Integ(
    lambda: infected_mortality_rate(), lambda: 0, "_integ_infected_mortality"
)


@component.add(
    name="Quarantine",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_quarantine": 1},
    other_deps={
        "_integ_quarantine": {
            "initial": {},
            "step": {
                "quarantine_rate": 1,
                "quarantine_recovery_rate": 1,
                "quarantine_mortality_rate": 1,
            },
        }
    },
)
def quarantine():
    return _integ_quarantine()


_integ_quarantine = Integ(
    lambda: quarantine_rate()
    - quarantine_recovery_rate()
    - quarantine_mortality_rate(),
    lambda: 0,
    "_integ_quarantine",
)


@component.add(
    name="quarantine death rate",
    units="1/day",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def quarantine_death_rate():
    return 0.001


@component.add(
    name="Quarantine Deaths",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_quarantine_deaths": 1},
    other_deps={
        "_integ_quarantine_deaths": {
            "initial": {},
            "step": {"quarantine_mortality_rate": 1},
        }
    },
)
def quarantine_deaths():
    return _integ_quarantine_deaths()


_integ_quarantine_deaths = Integ(
    lambda: quarantine_mortality_rate(), lambda: 0, "_integ_quarantine_deaths"
)


@component.add(
    name="Quarantine mortality rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"quarantine": 1, "quarantine_death_rate": 1},
)
def quarantine_mortality_rate():
    return quarantine() * quarantine_death_rate()


@component.add(
    name="Infected",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_infected": 1},
    other_deps={
        "_integ_infected": {
            "initial": {"initial_infected": 1},
            "step": {
                "infection_rate": 1,
                "infected_mortality_rate": 1,
                "quarantine_rate": 1,
                "recovery_rate": 1,
            },
        }
    },
)
def infected():
    return _integ_infected()


_integ_infected = Integ(
    lambda: infection_rate()
    - infected_mortality_rate()
    - quarantine_rate()
    - recovery_rate(),
    lambda: initial_infected(),
    "_integ_infected",
)


@component.add(
    name="Incubation period",
    units="day",
    limits=(0.0, 14.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def incubation_period():
    return 4


@component.add(
    name="Recovered",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_recovered": 1},
    other_deps={
        "_integ_recovered": {
            "initial": {},
            "step": {"quarantine_recovery_rate": 1, "recovery_rate": 1},
        }
    },
)
def recovered():
    return _integ_recovered()


_integ_recovered = Integ(
    lambda: quarantine_recovery_rate() + recovery_rate(), lambda: 0, "_integ_recovered"
)


@component.add(
    name="pathogen load",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def pathogen_load():
    return 0.4


@component.add(
    name="init s",
    units="cattle",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"initial_population": 1, "initial_infected": 1},
)
def init_s():
    return initial_population() - initial_infected()


@component.add(
    name="vaccination coverage",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def vaccination_coverage():
    return 0.4


@component.add(
    name="Exposed",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_exposed": 1},
    other_deps={
        "_integ_exposed": {
            "initial": {},
            "step": {"exposure_rate": 1, "infection_rate": 1},
        }
    },
)
def exposed():
    return _integ_exposed()


_integ_exposed = Integ(
    lambda: exposure_rate() - infection_rate(), lambda: 50, "_integ_exposed"
)


@component.add(
    name="initial infected",
    units="cattle",
    limits=(0.0, np.nan),
    comp_type="Constant",
    comp_subtype="Normal",
)
def initial_infected():
    return 1


@component.add(
    name="initial population",
    units="cattle",
    limits=(0.0, np.nan),
    comp_type="Constant",
    comp_subtype="Normal",
)
def initial_population():
    return 10000


@component.add(
    name="quarantine recovery rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"quarantine": 1, "average_time_to_recovery_in_quarantine": 1},
)
def quarantine_recovery_rate():
    return quarantine() / average_time_to_recovery_in_quarantine()


@component.add(
    name="Recovery Rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"infected": 1, "average_infection_time": 1},
)
def recovery_rate():
    return infected() * (1 / average_infection_time())


@component.add(
    name="cattle sold", units="head", comp_type="Constant", comp_subtype="Normal"
)
def cattle_sold():
    return 50


@component.add(
    name="contact rate",
    units="1/day",
    limits=(0.0, 50.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def contact_rate():
    return 10


@component.add(
    name="average time to recovery in quarantine",
    units="day",
    limits=(0.0, 20.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_time_to_recovery_in_quarantine():
    return 7


@component.add(
    name="average infection time",
    units="day",
    limits=(0.0, 20.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_infection_time():
    return 7


@component.add(
    name="average time to quarantine",
    units="day",
    limits=(0.0, 20.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def average_time_to_quarantine():
    return 4


@component.add(
    name="Quarantine rate",
    units="cattle/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"infected": 1, "average_time_to_quarantine": 1},
)
def quarantine_rate():
    return infected() / average_time_to_quarantine()
