
from dataclasses import dataclass, field
from typing import Optional
from math import isfinite
from drafter import *

set_website_title("Chemistry Assistant")
set_site_information(
    author="Matthew Fitzgerald",
    description="Stoichiometric calculator.",
    sources="Thanks to the Drafter docs and my amazing professor.",
    planning=[],
    links=[]
)
hide_debug_information()
set_website_framed(False)
# ---------------------------------------------------------
# WEBSITE CONFIGURATION
# ---------------------------------------------------------

SITE_TITLE = "ChemistryLab | Stoichiometry Assistant"

set_website_title(SITE_TITLE)
set_website_style("simple")
set_website_framed(False)

# Custom CSS gives the website a consistent scientific look.
# This is presentation code and does not affect calculations.
add_website_css(
    "body",
    "background-color: #f1f5f9; color: #183047; "
    "font-family: Arial, sans-serif;"
)

add_website_css(
    "button",
    "background-color: #087f8c; color: white; "
    "border-radius: 8px; padding: 10px 18px; "
    "border: none; font-weight: bold;"
)

add_website_css(
    "input",
    "border: 1px solid #cbd5e1; border-radius: 6px; "
    "padding: 9px; margin: 5px;"
)

add_website_css(
    "table",
    "background-color: white; border-collapse: collapse; "
    "width: 100%; margin-top: 12px;"
)

add_website_css(
    "th",
    "background-color: #183047; color: white; "
    "padding: 12px;"
)

add_website_css(
    "td",
    "padding: 10px; border-bottom: 1px solid #dbe3eb;"
)

add_website_css(
    "a",
    "color: #087f8c; font-weight: bold;"
)


# ---------------------------------------------------------
# DATACLASSES
# ---------------------------------------------------------

@dataclass
class Chemical:
    """Store the information entered for one chemical compound."""

    formula: str
    coefficient: float
    molar_mass_g_mol: float
    starting_mass_g: float
    harvested_mass_g: float = 0.0


@dataclass
class ReactantResult:
    """Store the calculated results for one reactant."""

    formula: str
    starting_moles: float
    remaining_moles: float
    remaining_mass_g: float
    status: str


@dataclass
class ProductResult:
    """Store the calculated results for one product."""

    formula: str
    theoretical_mass_g: float
    harvested_mass_g: float
    percent_yield: float
    heat_per_mole_kj: float


@dataclass
class CalculationResult:
    """Store all results from one stoichiometry calculation."""

    limiting_reactant: str
    reaction_extent_mol: float
    reaction_type: str
    total_heat_kj: float
    reactant_results: list[ReactantResult] = field(
        default_factory=list
    )
    product_results: list[ProductResult] = field(
        default_factory=list
    )


@dataclass
class ReactionRecord:
    """Store a completed reaction in the user's history."""

    reaction_name: str
    equation: str
    limiting_reactant: str
    yield_summary: str
    total_heat_kj: float


# ---------------------------------------------------------
# APPLICATION STATE
# ---------------------------------------------------------

@dataclass
class State:
    """Store all information shared between website routes."""

    reaction_name: str = "Untitled Reaction"

    reactants: list[Chemical] = field(default_factory=list)

    products: list[Chemical] = field(default_factory=list)

    delta_h_kj_per_mol: float = 0.0

    latest_result: Optional[CalculationResult] = None

    latest_equation: str = ""

    history: list[ReactionRecord] = field(default_factory=list)

    status_message: str = ""


# ---------------------------------------------------------
# GENERAL HELPER FUNCTIONS
# ---------------------------------------------------------

def format_number(value: float) -> str:
    """Format a number to four decimal places for display."""

    return f"{value:,.4f}"


def format_coefficient(coefficient: float) -> str:
    """Format a reaction coefficient without unnecessary zeros."""

    if abs(coefficient - 1.0) < 0.000001:
        return ""

    return f"{coefficient:g} "


def create_equation(
    reactants: list[Chemical],
    products: list[Chemical]
) -> str:
    """Create a readable chemical equation from compound lists."""

    reactant_side = " + ".join(
        format_coefficient(chemical.coefficient)
        + chemical.formula
        for chemical in reactants
    )

    product_side = " + ".join(
        format_coefficient(chemical.coefficient)
        + chemical.formula
        for chemical in products
    )

    return reactant_side + " → " + product_side


def page_shell(
    state: State,
    title: str,
    content: list
) -> Page:
    """Create a consistent layout and navigation for every page."""

    navigation = [
        Link("Home", "index"),
        "  |  ",
        Link("Setup", "reaction_setup"),
        "  |  ",
        Link("Reactants", "reactant_info"),
        "  |  ",
        Link("Products", "product_info"),
        "  |  ",
        Link("Conditions", "conditions"),
        "  |  ",
        Link("Results", "results"),
        "  |  ",
        Link("Analysis", "analysis"),
        "  |  ",
        Link("History", "history"),
        HorizontalRule()
    ]

    return Page(
        state,
        [
            Header("CHEMISTRYLAB"),
            "STOICHIOMETRY ASSISTANT  |  CHEMISTRY 2e\n",
        ] + navigation + [
            Header(title)
        ] + content
    )


def build_chemical(
    formula: str,
    coefficient: float,
    molar_mass: float,
    mass: float,
    is_product: bool,
    allow_empty: bool
) -> tuple[Optional[Chemical], str]:
    """Validate user input and create a Chemical instance."""

    formula = formula.strip()

    # An empty second compound means the user only has one.
    if not formula:
        if allow_empty:
            if (
                coefficient != 0
                or molar_mass != 0
                or mass != 0
            ):
                return None, (
                    "Enter a formula for the second compound "
                    "or leave all its fields at zero."
                )

            return None, ""

        return None, "The first compound's formula is required."

    if coefficient <= 0:
        return None, "Every compound needs a positive coefficient."

    if molar_mass <= 0:
        return None, "Molecular mass must be greater than zero."

    if not isfinite(coefficient) or not isfinite(molar_mass):
        return None, "Enter valid finite numerical values."

    if not isfinite(mass) or mass < 0:
        return None, "Masses must be finite and cannot be negative."

    if not is_product and mass <= 0:
        return None, "Starting reactant mass must be greater than zero."

    return Chemical(
        formula,
        coefficient,
        molar_mass,
        0.0 if is_product else mass,
        mass if is_product else 0.0
    ), ""


# ---------------------------------------------------------
# CHEMISTRY CALCULATION FUNCTIONS
# ---------------------------------------------------------

def calculate_stoichiometry(
    reactants: list[Chemical],
    products: list[Chemical],
    delta_h: float
) -> CalculationResult:
    """Calculate limiting reactants, yields, and reaction heat."""

    if not reactants or not products:
        raise ValueError(
            "At least one reactant and one product are required."
        )

    # Calculate how many moles of reaction each reactant
    # could support based on its balanced coefficient.
    reaction_amounts = []

    for reactant in reactants:
        available_moles = (
            reactant.starting_mass_g
            / reactant.molar_mass_g_mol
        )

        reaction_amounts.append(
            available_moles / reactant.coefficient
        )

    # The smallest reaction amount identifies the limiting reagent.
    reaction_extent = min(reaction_amounts)

    limiting_index = reaction_amounts.index(reaction_extent)

    if len(reactants) == 1:
        limiting_reactant = reactants[0].formula

    elif abs(
        reaction_amounts[0] - reaction_amounts[1]
    ) < 0.000000001:
        limiting_reactant = "Both reactants"

    else:
        limiting_reactant = reactants[limiting_index].formula

    # Calculate the remaining mass of each reactant.
    reactant_results = []

    for reactant in reactants:
        starting_moles = (
            reactant.starting_mass_g
            / reactant.molar_mass_g_mol
        )

        consumed_moles = (
            reactant.coefficient * reaction_extent
        )

        remaining_moles = max(
            0.0,
            starting_moles - consumed_moles
        )

        remaining_mass = (
            remaining_moles * reactant.molar_mass_g_mol
        )

        if remaining_moles < 0.000000001:
            status = "Limiting"
        else:
            status = "Excess"

        reactant_results.append(
            ReactantResult(
                reactant.formula,
                starting_moles,
                remaining_moles,
                remaining_mass,
                status
            )
        )

    # Calculate the theoretical yield of every product.
    product_results = []

    for product in products:
        theoretical_moles = (
            product.coefficient * reaction_extent
        )

        theoretical_mass = (
            theoretical_moles * product.molar_mass_g_mol
        )

        if theoretical_mass > 0:
            percent_yield = (
                product.harvested_mass_g
                / theoretical_mass
            ) * 100
        else:
            percent_yield = 0.0

        # Delta H is given per mole of reaction as written.
        heat_per_mole = (
            delta_h / product.coefficient
        )

        product_results.append(
            ProductResult(
                product.formula,
                theoretical_mass,
                product.harvested_mass_g,
                percent_yield,
                heat_per_mole
            )
        )

    # Determine the thermochemical classification.
    if delta_h < 0:
        reaction_type = "Exothermic"

    elif delta_h > 0:
        reaction_type = "Endothermic"

    else:
        reaction_type = "Thermoneutral"

    total_heat = delta_h * reaction_extent

    return CalculationResult(
        limiting_reactant,
        reaction_extent,
        reaction_type,
        total_heat,
        reactant_results,
        product_results
    )


def create_history_record(
    state: State,
    result: CalculationResult
) -> ReactionRecord:
    """Convert the latest calculation into a history record."""

    yield_parts = []

    for product in result.product_results:
        yield_parts.append(
            product.formula
            + ": "
            + format_number(product.percent_yield)
            + "%"
        )

    yield_summary = ", ".join(yield_parts)

    return ReactionRecord(
        state.reaction_name,
        state.latest_equation,
        result.limiting_reactant,
        yield_summary,
        result.total_heat_kj
    )


# ---------------------------------------------------------
# PAGE 1: HOME PAGE
# ---------------------------------------------------------

@route
def index(state: State) -> Page:
    """Display the main dashboard and project introduction."""

    return page_shell(
        state,
        "Welcome to ChemistryLab",
        [
            "Analyze chemical reactions with an organized "
            "stoichiometry calculator.\n",

            Header("YOUR CHEMISTRY WORKSPACE"),

            "Enter a balanced chemical equation, provide the "
            "necessary measurements, and receive a detailed "
            "breakdown of your reaction.\n",

            Header("CALCULATION FEATURES"),

            "01  Limiting and excess reactants\n",
            "02  Theoretical product yields\n",
            "03  Percent yields for each product\n",
            "04  Remaining reactant masses\n",
            "05  Exothermic and endothermic reactions\n",
            "06  Heat flow per mole of product\n",

            HorizontalRule(),

            Header("GET STARTED"),

            "Begin by entering the name of your reaction.\n",

            Button("Start a New Reaction", "reaction_setup"),

            Button("View Previous Reactions", "history"),

            "\n",

            "Current reaction: " + state.reaction_name
        ]
    )


# ---------------------------------------------------------
# PAGE 2: REACTION SETUP
# ---------------------------------------------------------

@route
def reaction_setup(state: State) -> Page:
    """Ask the user to name the chemical reaction."""

    return page_shell(
        state,
        "Step 1 | Reaction Setup",
        [
            "Give your reaction a name so that you can "
            "identify it in your history.\n",

            "Reaction Name:\n",

            TextBox("reaction_name", state.reaction_name),

            "\n",

            Button("Continue to Reactants", "save_reaction_name"),

            "Your reaction must already be balanced. "
            "Enter its coefficients on the following pages."
        ]
    )


@route
def save_reaction_name(
    state: State,
    reaction_name: str
) -> Page:
    """Save the reaction name and continue to reactant inputs."""

    if not reaction_name.strip():
        state.status_message = "Please enter a reaction name."
        return reaction_setup(state)

    state.reaction_name = reaction_name.strip()
    state.status_message = ""

    return reactant_info(state)


# ---------------------------------------------------------
# PAGE 3: REACTANT INFORMATION
# ---------------------------------------------------------

@route
def reactant_info(state: State) -> Page:
    """Display input fields for one or two reactants."""

    return page_shell(
        state,
        "Step 2 | Reactant Information",
        [
            "Enter the information for your reactants.\n",

            "Molecular masses must be entered in g/mol.\n",
            "Starting masses must be entered in grams.\n",

            Header("REACTANT 1"),

            "Chemical formula:\n",
            TextBox("r1_formula", "H2"),

            "Balanced coefficient:\n",
            TextBox("r1_coefficient", 2.0, "number"),

            "Molecular mass (g/mol):\n",
            TextBox("r1_molar_mass", 2.016, "number"),

            "Starting mass (g):\n",
            TextBox("r1_mass", 10.0, "number"),

            HorizontalRule(),

            Header("REACTANT 2"),

            "Chemical formula (leave blank if unused):\n",
            TextBox("r2_formula", ""),

            "Balanced coefficient (0 if unused):\n",
            TextBox("r2_coefficient", 0.0, "number"),


            "Molecular mass (g/mol):\n",
            TextBox("r2_molar_mass", 0.0, "number"),


            "Starting mass (g):\n",
            TextBox("r2_mass", 0.0, "number"),

            HorizontalRule(),

            Button("Save Reactants", "save_reactants"),

            state.status_message
        ]
    )


@route
def save_reactants(
    state: State,
    r1_formula: str,
    r1_coefficient: float,
    r1_molar_mass: float,
    r1_mass: float,
    r2_formula: str,
    r2_coefficient: float,
    r2_molar_mass: float,
    r2_mass: float
) -> Page:
    """Validate and save both reactant entries."""

    reactant_one, error = build_chemical(
        r1_formula,
        r1_coefficient,
        r1_molar_mass,
        r1_mass,
        False,
        False
    )

    if error:
        state.status_message = error
        return reactant_info(state)

    reactant_two, error = build_chemical(
        r2_formula,
        r2_coefficient,
        r2_molar_mass,
        r2_mass,
        False,
        True
    )

    if error:
        state.status_message = error
        return reactant_info(state)

    state.reactants = [reactant_one]

    if reactant_two is not None:
        state.reactants.append(reactant_two)

    state.latest_result = None
    state.status_message = ""

    return product_info(state)


# ---------------------------------------------------------
# PAGE 4: PRODUCT INFORMATION
# ---------------------------------------------------------

@route
def product_info(state: State) -> Page:
    """Display input fields for one or two products."""

    return page_shell(
        state,
        "Step 3 | Product Information",
        [
            "Enter the molecular masses and harvested amounts "
            "of your products.\n",

            "Molecular masses must be entered in g/mol.\n",
            "Harvested amounts must be entered in grams.\n",

            Header("PRODUCT 1"),

            "Chemical formula:\n",
            TextBox("p1_formula", "H2O"),

            "Balanced coefficient:\n",
            TextBox("p1_coefficient", 2.0, "number"),

            "Molecular mass (g/mol):\n",
            TextBox("p1_molar_mass", 18.015, "number"),

            "Harvested amount (g):\n",
            TextBox("p1_mass", 0.0, "number"),

            HorizontalRule(),

            Header("PRODUCT 2"),

            "Chemical formula (leave blank if unused):\n",
            TextBox("p2_formula", ""),

            "Balanced coefficient (0 if unused):\n",
            TextBox("p2_coefficient", 0.0, "number"),

            "Molecular mass (g/mol):\n",
            TextBox("p2_molar_mass", 0.0, "number"),

            "Harvested amount (g):\n",
            TextBox("p2_mass", 0.0, "number"),

            HorizontalRule(),

            Button("Save Products", "save_products"),

            state.status_message
        ]
    )


@route
def save_products(
    state: State,
    p1_formula: str,
    p1_coefficient: float,
    p1_molar_mass: float,
    p1_mass: float,
    p2_formula: str,
    p2_coefficient: float,
    p2_molar_mass: float,
    p2_mass: float
) -> Page:
    """Validate and save both product entries."""

    product_one, error = build_chemical(
        p1_formula,
        p1_coefficient,
        p1_molar_mass,
        p1_mass,
        True,
        False
    )

    if error:
        state.status_message = error
        return product_info(state)

    product_two, error = build_chemical(
        p2_formula,
        p2_coefficient,
        p2_molar_mass,
        p2_mass,
        True,
        True
    )

    if error:
        state.status_message = error
        return product_info(state)

    state.products = [product_one]

    if product_two is not None:
        state.products.append(product_two)

    state.latest_result = None
    state.status_message = ""

    return conditions(state)


# ---------------------------------------------------------
# PAGE 5: REACTION CONDITIONS
# ---------------------------------------------------------

@route
def conditions(state: State) -> Page:
    """Ask the user to enter the reaction enthalpy."""

    return page_shell(
        state,
        "Step 4 | Reaction Conditions",
        [
            Header("HEAT OF REACTION"),

            "Enter the reaction enthalpy, ΔH, in "
            "kJ/mol of reaction as written in your "
            "balanced equation.\n",

            "A negative value indicates an exothermic reaction.\n",
            "A positive value indicates an endothermic reaction.\n",

            "ΔH (kJ/mol of reaction):\n",

            TextBox(
                "delta_h",
                state.delta_h_kj_per_mol,
                "number"
            ),

            "\n",

            Button("Calculate Reaction", "save_conditions"),

            state.status_message
        ]
    )


@route
def save_conditions(
    state: State,
    delta_h: float
) -> Page:
    """Save the reaction enthalpy and calculate the results."""

    if not isfinite(delta_h):
        state.status_message = "Enter a valid ΔH value."
        return conditions(state)

    state.delta_h_kj_per_mol = delta_h
    state.status_message = ""
    
    return results(state)


# ---------------------------------------------------------
# PAGE 6: CALCULATION RESULTS
# ---------------------------------------------------------

@route
def results(state: State) -> Page:
    """Calculate and display the reaction's stoichiometry."""

    if not state.reactants or not state.products:
        return page_shell(
            state,
            "Calculation Results",
            [
                "Please enter your reaction information first.\n",
                Button("Reaction Setup", "reaction_setup")
            ]
        )

    result = calculate_stoichiometry(
        state.reactants,
        state.products,
        state.delta_h_kj_per_mol
    )

    state.latest_result = result

    state.latest_equation = create_equation(
        state.reactants,
        state.products
    )

    # Add the completed calculation to reaction history.
    state.history.append(
        create_history_record(state, result)
    )

    content = [
        Header("REACTION EQUATION"),

        state.latest_equation + "\n",

        Header("LIMITING REACTANT"),

        "Limiting reactant: "
        + result.limiting_reactant
        + "\n",

        "Reaction extent: "
        + format_number(result.reaction_extent_mol)
        + " mol\n",

        HorizontalRule(),

        Header("REACTANT BREAKDOWN"),

        Table(
            [
                [
                    item.formula,
                    format_number(item.starting_moles),
                    format_number(item.remaining_moles),
                    format_number(item.remaining_mass_g),
                    item.status
                ]
                for item in result.reactant_results
            ],
            [
                "Reactant",
                "Initial Moles",
                "Remaining Moles",
                "Remaining Mass (g)",
                "Status"
            ]
        ),

        HorizontalRule(),

        Header("PRODUCT YIELDS"),

        Table(
            [
                [
                    item.formula,
                    format_number(item.theoretical_mass_g),
                    format_number(item.harvested_mass_g),
                    format_number(item.percent_yield) + "%"
                ]
                for item in result.product_results
            ],
            [
                "Product",
                "Theoretical Yield (g)",
                "Harvested (g)",
                "Percent Yield"
            ]
        ),

        HorizontalRule(),

        Header("THERMOCHEMISTRY"),

        "Reaction classification: "
        + result.reaction_type
        + "\n",

        "Total heat flow: "
        + format_number(result.total_heat_kj)
        + " kJ\n",

        Button("View Detailed Heat Analysis", "analysis"),

        Button("View Reaction History", "history"),

        Button("Return Home", "index")
    ]

    return page_shell(
        state,
        "Calculation Results",
        content
    )


# ---------------------------------------------------------
# PAGE 7: DETAILED REACTION ANALYSIS
# ---------------------------------------------------------

@route
def analysis(state: State) -> Page:
    """Display detailed thermochemical calculations."""

    if state.latest_result is None:
        return page_shell(
            state,
            "Reaction Analysis",
            [
                "No completed calculation is available.\n",
                Button("Calculate a Reaction", "reaction_setup")
            ]
        )

    result = state.latest_result

    content = [
        Header("REACTION CLASSIFICATION"),

        result.reaction_type + "\n",

        "Entered ΔH: "
        + format_number(state.delta_h_kj_per_mol)
        + " kJ/mol of reaction\n",

        "Total heat flow: "
        + format_number(result.total_heat_kj)
        + " kJ\n",

        HorizontalRule(),

        Header("HEAT FLOW PER MOLE OF PRODUCT"),

        "The heat of reaction is divided by each product's "
        "balanced coefficient to determine the heat per mole "
        "of that product.\n",

        Table(
            [
                [
                    product.formula,
                    format_number(product.heat_per_mole_kj)
                    + " kJ/mol"
                ]
                for product in result.product_results
            ],
            ["Product", "Heat per Mole of Product"]
        ),

        HorizontalRule(),

        Header("INTERPRETATION"),

        "Exothermic reactions release heat.\n",
        "Endothermic reactions absorb heat.\n",

        "The total heat is calculated by multiplying ΔH "
        "by the reaction extent.\n",

        Button("Back to Results", "results"),

        Button("Return Home", "index")
    ]

    return page_shell(
        state,
        "Detailed Reaction Analysis",
        content
    )


# ---------------------------------------------------------
# PAGE 8: REACTION HISTORY
# ---------------------------------------------------------

@route
def history(state: State) -> Page:
    """Display previously completed chemical reactions."""

    content = [
        Header("YOUR PREVIOUS CALCULATIONS"),

        "Review the reactions that you have calculated "
        "during this session.\n"
    ]

    if state.history:
        history_rows = []

        # Iterate through the list of ReactionRecord instances.
        for record in state.history:
            history_rows.append(
                [
                    record.reaction_name,
                    record.equation,
                    record.limiting_reactant,
                    record.yield_summary,
                    format_number(record.total_heat_kj) + " kJ"
                ]
            )

            content.append(
                record.reaction_name
                + " — "
                + record.equation
                + "\n"
            )

        content.append(
            Table(
                history_rows,
                [
                    "Reaction",
                    "Equation",
                    "Limiting Reactant",
                    "Product Yields",
                    "Total Heat"
                ]
            )
        )

    else:
        content.append(
            "You have not calculated any reactions yet.\n"
        )

    content.extend(
        [
            HorizontalRule(),

            Button("Calculate Another Reaction", "reaction_setup"),

            Button("Return Home", "index")
        ]
    )

    return page_shell(
        state,
        "Reaction History",
        content
    )


# ---------------------------------------------------------
# UNIT TESTS
# ---------------------------------------------------------

# The following tests run when the program starts.
# They check the routes and chemistry calculations.



# Test the homepage.
assert_has(index(State()), "Welcome to ChemistryLab")


# Test the reaction setup page.
assert_has(
    reaction_setup(State()),
    "Reaction Setup"
)


# Test saving a reaction name.
assert_has(
    save_reaction_name(
        State(),
        "Hydrogen Combustion"
    ),
    "Reactant Information"
)


# Test the reactant information page.
assert_has(
    reactant_info(State()),
    "REACTANT 1"
)


# Test saving reactants.
test_state = State()
test_state.reaction_name = "Hydrogen Combustion"
assert_has(
    save_reactants(
        test_state,
        "H2", 2.0, 2.016, 10.0,
        "O2", 1.0, 32.0, 80.0
    ),
    "Product Information"
)

assert_equal(len(test_state.reactants), 2)


# Test the product information page.
assert_has(
    product_info(State()),
    "PRODUCT 1"
)


# Test saving products.
assert_has(
    save_products(
        test_state,
        "H2O", 2.0, 18.015, 5.0,
        "", 0.0, 0.0, 0.0
    ),
    "Reaction Conditions"
)

assert_equal(len(test_state.products), 1)


# Test the reaction conditions page.
assert_has(
    conditions(State()),
    "Reaction Conditions"
)


# Test the stoichiometry calculation.
test_result = calculate_stoichiometry(
    test_state.reactants,
    test_state.products,
    -483.6
)

assert_equal(
    test_result.limiting_reactant,
    "H2"
)

assert_equal(
    test_result.reaction_type,
    "Exothermic"
)



# Test the results route.
test_state.delta_h_kj_per_mol = -483.6

assert_has(
    results(test_state),
    "Limiting Reactant"
)

assert_equal(
    len(test_state.history),
    1
)


# Test the detailed analysis route.
assert_has(
    analysis(test_state),
    "Heat Flow Per Mole of Product"
)


# Test the history route.
assert_has(
    history(test_state),
    "Hydrogen Combustion"
)


# Test the chemical equation helper.
assert_equal(
    create_equation(
        [Chemical("H2", 2, 2.016, 10)],
        [Chemical("H2O", 2, 18.015, 0, 5)]
    ),
    "2 H2 → 2 H2O"
)


# ---------------------------------------------------------
# START THE WEBSITE
# ---------------------------------------------------------

start_server(State())
