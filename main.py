#Section 1 Imports, Constants, and Dataclasses
from bakery import assert_equal

from drafter import *
from dataclasses import dataclass, field

from chempy import Reaction, Substance
import requests

set_website_title("Chemistry Tutor")
set_site_information(
    author="Matthew Fitzgerald",
    description="Test your chemistry skills!",
    sources="Thanks to the Drafter docs and my professor.",
    planning="",
    links=["https://github.com/mafitz68/MAF-Chemistry"]
)
#hide_debug_information()
set_website_framed(False)

PUBCHEM_URL = (
    "https://pubchem.ncbi.nlm.nih.gov/rest/pug/"
    "compound/formula/"
)

DEFAULT_STATUS = (
    "Welcome! Enter reaction information to begin."
)


@dataclass
class ReactionRecord:
    """
    Stores information about a completed stoichiometry calculation.
    """
    equation: str
    limiting_reactant: str
    theoretical_yield: float
    percent_yield: float
    reaction_type: str


@dataclass
class State:
    """
    Stores all application data.
    """
    equation: str
    reactant1_formula: str
    reactant2_formula: str
    reactant1_mass: str
    reactant2_mass: str
    product_formula: str
    actual_product_mass: str
    heat_of_reaction: str
    notes: str
    save_history: bool

    records: list[ReactionRecord]

    latest_result: str
    status: str
    
#Section 2 Chemistry Helper Functions   
def get_molar_mass(formula: str) -> float:
    """
    Returns the molar mass of a chemical formula.
    """
    return Substance.from_formula(formula).mass


def calculate_moles(
    mass: float,
    molar_mass: float
) -> float:
    """
    Converts mass into moles.
    """
    return mass / molar_mass


def calculate_percent_yield(
    actual_yield: float,
    theoretical_yield: float
) -> float:
    """
    Calculates percent yield.
    """
    if theoretical_yield == 0:
        return 0.0

    return (
        actual_yield / theoretical_yield
    ) * 100


def determine_reaction_type(
    heat_of_reaction: float
) -> str:
    """
    Determines whether a reaction is
    exothermic or endothermic.
    """
    if heat_of_reaction < 0:
        return "Exothermic"

    return "Endothermic"

#Section 3 PubChem Helper
def get_pubchem_data(
    formula: str
) -> str:
    """
    Retrieves compound information
    from PubChem.
    """
    try:
        url = (
            f"{PUBCHEM_URL}{formula}/"
            "property/MolecularWeight,"
            "IUPACName/JSON"
        )

        response = requests.get(
            url,
            timeout=5
        )

        if response.status_code != 200:
            return "Compound not found."

        data = response.json()

        properties = (
            data["PropertyTable"]
            ["Properties"][0]
        )

        name = properties.get(
            "IUPACName",
            "Unknown"
        )

        weight = properties.get(
            "MolecularWeight",
            "Unknown"
        )

        return (
            f"Name: {name}\n"
            f"Molecular Weight: {weight}"
        )

    except Exception:
        return (
            "Could not connect "
            "to PubChem."
        )

#Section 4 Stoichiometry Calculation
def analyze_stoichiometry(
    reactant1_formula: str,
    reactant2_formula: str,
    reactant1_mass: float,
    reactant2_mass: float,
    product_formula: str,
    actual_product_mass: float,
    heat_of_reaction: float
) -> dict:
    """
    Calculates limiting reactant,
    theoretical yield,
    percent yield,
    and reaction type.
    """

    mm1 = get_molar_mass(
        reactant1_formula
    )

    mm2 = get_molar_mass(
        reactant2_formula
    )

    product_mm = get_molar_mass(
        product_formula
    )

    moles1 = calculate_moles(
        reactant1_mass,
        mm1
    )

    moles2 = calculate_moles(
        reactant2_mass,
        mm2
    )

    if moles1 < moles2:
        limiting = reactant1_formula
        limiting_moles = moles1
    else:
        limiting = reactant2_formula
        limiting_moles = moles2

    theoretical_yield = (
        limiting_moles *
        product_mm
    )

    percent = calculate_percent_yield(
        actual_product_mass,
        theoretical_yield
    )

    reaction_type = (
        determine_reaction_type(
            heat_of_reaction
        )
    )

    return {
        "limiting": limiting,
        "theoretical_yield":
            theoretical_yield,
        "percent_yield":
            percent,
        "reaction_type":
            reaction_type
    }

#SECTION 5: Unit Tests
assert_equal(
    round(get_molar_mass("H2O")),
    18
)

assert_equal(
    round(
        calculate_moles(
            18.015,
            18.015
        )
    ),
    1
)

assert_equal(
    calculate_percent_yield(
        90,
        100
    ),
    90.0
)

assert_equal(
    determine_reaction_type(
        -100
    ),
    "Exothermic"
)

assert_equal(
    determine_reaction_type(
        100
    ),
    "Endothermic"
)

#######################################################################
#SECTION 6: Home Page Route
@route
def index(
    state: State
) -> Page:
    """
    Home page.
    """

    return Page(state, [
        Header(
            "Chemistry Assistant"
        ),

        state.status,

        Button(
            "Reaction Calculator",
            reaction_page
        ),

        Button(
            "PubChem Lookup",
            lookup_page
        ),

        Button(
            "History",
            history_page
        ),

        Button(
            "Help",
            help_page
        ),

        Button(
            "About",
            about_page
        )
    ])

#SECTION 7: Reaction Input Page
@route
def reaction_page(
    state: State
) -> Page:
    """
    Data entry page.
    """

    return Page(state, [
        Header(
            "Reaction Calculator"
        ),

        "Balanced Equation",

        TextBox(
            "equation",
            state.equation
        ),

        "Reactant 1 Formula",

        TextBox(
            "reactant1_formula",
            state.reactant1_formula
        ),

        "Reactant 2 Formula",

        TextBox(
            "reactant2_formula",
            state.reactant2_formula
        ),

        "Product Formula",

        TextBox(
            "product_formula",
            state.product_formula
        ),

        "Reactant 1 Mass (g)",

        TextBox(
            "reactant1_mass",
            state.reactant1_mass
        ),

        "Reactant 2 Mass (g)",

        TextBox(
            "reactant2_mass",
            state.reactant2_mass
        ),

        "Actual Product Mass",

        TextBox(
            "actual_product_mass",
            state.actual_product_mass
        ),

        "Heat of Reaction",

        TextBox(
            "heat_of_reaction",
            state.heat_of_reaction
        ),

        "Notes",

        TextArea(
            "notes",
            state.notes
        ),

        CheckBox(
            "save_history",
            state.save_history
        ),

        Button(
            "Analyze",
            analyze_reaction
        ),

        Button(
            "Home",
            index
        )
    ])

#SECTION 8: Analysis Route
@route
def analyze_reaction(
    state: State,
    equation: str,
    reactant1_formula: str,
    reactant2_formula: str,
    product_formula: str,
    reactant1_mass: str,
    reactant2_mass: str,
    actual_product_mass: str,
    heat_of_reaction: str,
    notes: str,
    save_history: bool
) -> Page:
    """
    Performs calculations.
    """

    result = analyze_stoichiometry(
        reactant1_formula,
        reactant2_formula,
        float(reactant1_mass),
        float(reactant2_mass),
        product_formula,
        float(actual_product_mass),
        float(heat_of_reaction)
    )

    state.latest_result = (
        f"Limiting Reactant: "
        f"{result['limiting']}\n"
        f"Theoretical Yield: "
        f"{round(result['theoretical_yield'],2)} g\n"
        f"Percent Yield: "
        f"{round(result['percent_yield'],2)}%\n"
        f"Reaction Type: "
        f"{result['reaction_type']}"
    )

    if save_history:
        record = ReactionRecord(
            equation,
            result["limiting"],
            result["theoretical_yield"],
            result["percent_yield"],
            result["reaction_type"]
        )

        state.records.append(
            record
        )

    state.status = (
        "Analysis Complete"
    )

    return results_page(state)

#SECTION 9: Results Page
@route
def results_page(
    state: State
) -> Page:
    """
    Shows results.
    """

    return Page(state, [
        Header(
            "Results"
        ),

        state.latest_result,

        Button(
            "New Analysis",
            reaction_page
        ),

        Button(
            "Home",
            index
        )
    ])

#SECTION 10: History Page
@route
def history_page(
    state: State
) -> Page:
    """
    Displays history.
    """

    components = [
        Header("History")
    ]

    for record in state.records:

        components.append(
            f"{record.equation}"
        )

        components.append(
            f"Limiting Reactant: "
            f"{record.limiting_reactant}"
        )

        components.append(
            f"Percent Yield: "
            f"{round(record.percent_yield,2)}%"
        )

    components.append(
        Button(
            "Clear History",
            clear_history
        )
    )

    components.append(
        Button(
            "Home",
            index
        )
    )

    return Page(
        state,
        components
    )

#SECTION 11: Clear History Route
@route
def clear_history(
    state: State
) -> Page:
    """
    Clears history.
    """

    state.records = []

    state.status = (
        "History cleared."
    )

    return index(state)

#SECTION 12: PubChem Pages
@route
def lookup_page(
    state: State
) -> Page:
    """
    Lookup page.
    """

    return Page(state, [
        Header(
            "PubChem Lookup"
        ),

        TextBox(
            "formula",
            ""
        ),

        Button(
            "Search",
            lookup_result
        ),

        Button(
            "Home",
            index
        )
    ])


@route
def lookup_result(
    state: State,
    formula: str
) -> Page:
    """
    Lookup result page.
    """

    result = get_pubchem_data(
        formula
    )

    return Page(state, [
        Header(
            "Lookup Result"
        ),

        result,

        Button(
            "Lookup Again",
            lookup_page
        ),

        Button(
            "Home",
            index
        )
    ])

#SECTION 13: Help and About Pages
@route
def help_page(
    state: State
) -> Page:
    """
    Help page.
    """

    return Page(state, [
        Header("Help"),

        "Enter formulas such as H2O, "
        "CO2, or NH3.",

        "Mass values should be "
        "entered in grams.",

        Button(
            "Home",
            index
        )
    ])


@route
def about_page(
    state: State
) -> Page:
    """
    About page.
    """

    return Page(state, [
        Header("About"),

        "This application performs "
        "stoichiometry calculations "
        "using ChemPy and PubChem.",

        Button(
            "Home",
            index
        )
    ])

#SECTION 14: Start Server
start_server(
    State(
        equation="",
        reactant1_formula="",
        reactant2_formula="",
        reactant1_mass="",
        reactant2_mass="",
        product_formula="",
        actual_product_mass="",
        heat_of_reaction="",
        notes="",
        save_history=False,
        records=[],
        latest_result="",
        status=DEFAULT_STATUS
    )
)

