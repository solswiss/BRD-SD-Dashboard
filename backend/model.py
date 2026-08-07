"""
Python model 'SEIQR_linked.py'
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
    "final_time": lambda: 60,
    "time_step": lambda: 0.0625,
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
    name="ADG reduction loss",
    units="cattle",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"infected": 1, "adg_reduction_rate": 1},
)
def adg_reduction_loss():
    return infected() * (1 - adg_reduction_rate())


@component.add(
    name="ADG reduction rate",
    units="Dmnl",
    limits=(0.0, 0.5),
    comp_type="Constant",
    comp_subtype="Normal",
)
def adg_reduction_rate():
    return 0.08


@component.add(
    name="Healthcare cost",
    units="USD",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "vaccination_cost": 1,
        "susceptible": 1,
        "unit_cost_of_metaphylactic_amu": 1,
        "unit_cost_of_therapeutic_amu": 1,
        "infected": 1,
    },
)
def healthcare_cost():
    return (
        vaccination_cost()
        + unit_cost_of_metaphylactic_amu() * susceptible()
        + unit_cost_of_therapeutic_amu() * infected()
    )


@component.add(
    name="AMU Rate",
    units="grams/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"fractional_amu_rate_1": 1, "fractional_amu_rate_2": 1},
)
def amu_rate():
    return fractional_amu_rate_1() + fractional_amu_rate_2()


@component.add(
    name="Production Cost",
    units="USD",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"healthcare_cost": 1, "non_healthcare_cost": 1},
)
def production_cost():
    """Total cost of production."""
    return healthcare_cost() + non_healthcare_cost()


@component.add(
    name="Profit",
    units="USD",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_profit": 1},
    other_deps={"_integ_profit": {"initial": {}, "step": {"profitability_rate": 1}}},
)
def profit():
    """Net profit."""
    return _integ_profit()


_integ_profit = Integ(lambda: profitability_rate(), lambda: 1, "_integ_profit")


@component.add(
    name="Profitability rate",
    units="USD/Year",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "herd_revenue": 1,
        "production_cost": 1,
        "fractional_profitability_rate": 1,
    },
)
def profitability_rate():
    return (herd_revenue() - production_cost()) * fractional_profitability_rate()


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
    name="treatment rate",
    units="grams/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "infected": 1,
        "quarantine": 1,
        "treatment_dosage": 1,
        "usage_frequency_t": 1,
    },
)
def treatment_rate():
    return ((infected() + quarantine()) * treatment_dosage()) / usage_frequency_t()


@component.add(
    name="Unit cost of metaphylactic AMU",
    units="USD",
    limits=(0.0, 50.0, 10.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def unit_cost_of_metaphylactic_amu():
    return 10


@component.add(
    name="Cumulative antimicrobial usage",
    units="grams",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_cumulative_antimicrobial_usage": 1},
    other_deps={
        "_integ_cumulative_antimicrobial_usage": {
            "initial": {},
            "step": {"metaphylaxis_rate": 1, "treatment_rate": 1},
        }
    },
)
def cumulative_antimicrobial_usage():
    """Total antimicrobials administered over time."""
    return _integ_cumulative_antimicrobial_usage()


_integ_cumulative_antimicrobial_usage = Integ(
    lambda: amu_rate(), lambda: 0, "_integ_cumulative_antimicrobial_usage"
)


@component.add(
    name="unit cost of vaccine",
    units="USD",
    limits=(0.0, 50.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def unit_cost_of_vaccine():
    return 10


@component.add(
    name="Unit non healthcare cost",
    units="USD/cattle",
    limits=(500.0, 2000.0, 200.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def unit_non_healthcare_cost():
    return 1000


@component.add(
    name="loss rate",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "steer_heifer_value": 1,
        "mortality_loss": 1,
        "adg_reduction_loss": 1,
        "opportunity_cost": 1,
    },
)
def loss_rate():
    return (
        steer_heifer_value()
        * (adg_reduction_loss() + mortality_loss())
        * opportunity_cost()
    )


@component.add(
    name="Metaphylactic usage",
    units="grams",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_metaphylactic_usage": 1},
    other_deps={
        "_integ_metaphylactic_usage": {
            "initial": {},
            "step": {"metaphylaxis_rate": 1, "fractional_amu_rate_1": 1},
        }
    },
)
def metaphylactic_usage():
    """Preventive antimicrobial administration."""
    return _integ_metaphylactic_usage()


_integ_metaphylactic_usage = Integ(
    lambda: metaphylaxis_rate() - fractional_amu_rate_1(),
    lambda: 0,
    "_integ_metaphylactic_usage",
)


@component.add(
    name="Revenue rate",
    units="USD",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"recovered": 1, "steer_heifer_value": 1},
)
def revenue_rate():
    return recovered() * steer_heifer_value()


@component.add(
    name="fractional AMU rate 1",
    units="grams/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"metaphylactic_usage": 1},
)
def fractional_amu_rate_1():
    return metaphylactic_usage()


@component.add(
    name="fractional AMU rate 2",
    units="grams/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"therapeutic_usage": 1},
)
def fractional_amu_rate_2():
    return therapeutic_usage()


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
    name="fractional profitability rate",
    units="USD/Year",
    comp_type="Constant",
    comp_subtype="Normal",
)
def fractional_profitability_rate():
    return 1


@component.add(
    name="Therapeutic usage",
    units="grams",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_therapeutic_usage": 1},
    other_deps={
        "_integ_therapeutic_usage": {
            "initial": {},
            "step": {"treatment_rate": 1, "fractional_amu_rate_2": 1},
        }
    },
)
def therapeutic_usage():
    """Treatment antimicrobial administration."""
    return _integ_therapeutic_usage()


_integ_therapeutic_usage = Integ(
    lambda: treatment_rate() - fractional_amu_rate_2(),
    lambda: 0,
    "_integ_therapeutic_usage",
)


@component.add(
    name="Herd Revenue",
    units="USD",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_herd_revenue": 1},
    other_deps={"_integ_herd_revenue": {"initial": {}, "step": {"revenue_rate": 1}}},
)
def herd_revenue():
    """Total revenue from herd production."""
    return _integ_herd_revenue()


_integ_herd_revenue = Integ(lambda: revenue_rate(), lambda: 1, "_integ_herd_revenue")


@component.add(
    name="Total Production Loss",
    units="USD",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_total_production_loss": 1},
    other_deps={
        "_integ_total_production_loss": {"initial": {}, "step": {"loss_rate": 1}}
    },
)
def total_production_loss():
    return _integ_total_production_loss()


_integ_total_production_loss = Integ(
    lambda: loss_rate(), lambda: 1, "_integ_total_production_loss"
)


@component.add(
    name="Usage frequency T",
    units="day",
    limits=(0.0, 10.0, 2.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def usage_frequency_t():
    return 1


@component.add(
    name="metaphylaxis dosage",
    units="grams/cattle",
    limits=(0.0, 10.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def metaphylaxis_dosage():
    return 0.1


@component.add(
    name="treatment dosage",
    units="grams/cattle",
    limits=(0.0, 10.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def treatment_dosage():
    return 0.1


@component.add(
    name="mortality loss",
    units="cattle",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"infected_mortality": 1},
)
def mortality_loss():
    """Cumulative mortality attributable to infection."""
    return infected_mortality()


@component.add(
    name="Non healthcare cost",
    units="USD",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"unit_non_healthcare_cost": 1, "current_population": 1},
)
def non_healthcare_cost():
    return unit_non_healthcare_cost() * current_population()


@component.add(
    name="Unit cost of therapeutic AMU",
    units="USD",
    limits=(0.0, 50.0, 10.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def unit_cost_of_therapeutic_amu():
    return 10


@component.add(
    name="Vaccination cost",
    units="USD",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "unit_cost_of_vaccine": 1,
        "current_population": 1,
        "vaccination_coverage": 1,
    },
)
def vaccination_cost():
    return unit_cost_of_vaccine() * current_population() * vaccination_coverage()


@component.add(
    name="metaphylaxis rate",
    units="grams/day",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "susceptible": 1,
        "risk_factor_score": 1,
        "metaphylaxis_dosage": 1,
        "usage_frequency_m": 1,
    },
)
def metaphylaxis_rate():
    return (
        susceptible() * risk_factor_score() * metaphylaxis_dosage()
    ) / usage_frequency_m()


@component.add(
    name="Usage frequency M",
    units="day",
    limits=(0.0, 10.0, 2.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def usage_frequency_m():
    return 1


@component.add(
    name="Steer heifer value",
    units="USD",
    limits=(1000.0, 4000.0, 500.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def steer_heifer_value():
    return 2500


@component.add(
    name="opportunity cost",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def opportunity_cost():
    """
    10% opportunity cost
    """
    return 0.1


@component.add(
    name="transmission probability",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={"risk_factor_score": 1, "vaccination_coverage": 1, "infectivity": 1},
)
def transmission_probability():
    return risk_factor_score() * (1 - vaccination_coverage()) * infectivity()


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
    """Rate at which susceptible animals acquire infection."""
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
    name="Risk factor score",
    units="Dmnl",
    comp_type="Auxiliary",
    comp_subtype="Normal",
    depends_on={
        "age_score": 1,
        "commingling_score": 1,
        "preconditioning_score": 1,
        "season_score": 1,
        "transportation_score": 1,
        "weather_score": 1,
    },
)
def risk_factor_score():
    """Composite risk assessment based on epidemiological and economic factors."""
    return (
        age_score()
        + commingling_score()
        + preconditioning_score()
        + season_score()
        + transportation_score()
        + weather_score()
    ) / 7


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
    name="Susceptible",
    units="cattle",
    comp_type="Stateful",
    comp_subtype="Integ",
    depends_on={"_integ_susceptible": 1},
    other_deps={
        "_integ_susceptible": {"initial": {"init_s": 1}, "step": {"exposure_rate": 1}}
    },
)
def susceptible():
    return _integ_susceptible()


_integ_susceptible = Integ(
    lambda: -exposure_rate(), lambda: init_s(), "_integ_susceptible"
)


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
    name="preconditioning score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def preconditioning_score():
    return 1


@component.add(
    name="cattle sold", units="head", comp_type="Constant", comp_subtype="Normal"
)
def cattle_sold():
    return 50


@component.add(
    name="Days on feed", units="day", comp_type="Constant", comp_subtype="Normal"
)
def days_on_feed():
    return 10


@component.add(
    name="age score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def age_score():
    return 1


@component.add(
    name="season score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def season_score():
    return 1


@component.add(
    name="commingling score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def commingling_score():
    return 1


@component.add(
    name="weather score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def weather_score():
    return 0.5


@component.add(
    name="contact rate",
    units="1/day",
    limits=(0.0, 50.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def contact_rate():
    """Contact frequency in herd."""
    return 10


@component.add(
    name="transportation score",
    units="Dmnl",
    limits=(0.0, 1.0),
    comp_type="Constant",
    comp_subtype="Normal",
)
def transportation_score():
    return 1


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
