
"""
main.py

Automated Chemistry Assistant

A Drafter website that calculates chemical yields,
limiting reactants, excess reactants, and reaction heat.
"""

from dataclasses import dataclass, field

from drafter import *

from chemistry import (
    Compound,
    parse_equation,
    calculate_stoichiometry
)


@dataclass
class ReactionRecord:
    """Stores a previously completed reaction calculation."""

    equation: str
    product: str
    theoretical_yield: float
    harvested_mass: float
    percent_yield: float


@dataclass
class State:
    """Stores all information needed by the website."""

    equation: str = ""

    reactants: list[Compound] = field(default_factory=list)
    products: list[Compound] = field(default_factory=list)

    selected_product: str = ""
    harvested_mass_g: float = 0.0
    delta_h: float = 0.0

    results: dict = field(default_factory=dict)

    result_summary: str = ""
    error_message: str = ""

    history: list[ReactionRecord] = field(default_factory=list)


def create_navigation() -> list:
    """Create the navigation buttons used throughout the website."""

    return [
        Button("Home", "index"),
        Button("New Reaction", "reaction_setup"),
        Button("History", "history")
    ]


def create_mass_template(reactants: list[Compound]) -> str:
    """Create an example reactant mass input for the user."""

    template = ""

    for compound in reactants:
        template += compound.formula + "=0\n"

    return template


def save_reactant_masses(
    reactants: list[Compound],
    mass_text: str
) -> None:
    """
    Read reactant masses from the user's text area.

    Expected format:
    H2=4.0
    O2=32.0
    """

    entered_masses = {}

    for line in mass_text.splitlines():
        if line.strip() == "":
            continue

        if "=" not in line:
            raise ValueError(
                "Use the format Formula=Mass for every reactant."
            )

        formula, mass_text_value = line.split("=", 1)

        formula = formula.strip()

        if formula in entered_masses:
            raise ValueError("A reactant was entered twice.")

        try:
            mass = float(mass_text_value.strip())
        except ValueError:
            raise ValueError("Reactant masses must be numbers.")

        if mass <= 0:
            raise ValueError("Reactant masses must be positive.")

        entered_masses[formula] = mass

    if len(entered_masses) != len(reactants):
        raise ValueError(
            "Enter a mass for every reactant exactly once."
        )

    for compound in reactants:
        if compound.formula not in entered_masses:
            raise ValueError(
                "Missing mass for " + compound.formula
            )

        compound.starting_mass_g = (
            entered_masses[compound.formula]
        )


@route
def index(state: State) -> Page:
    """Display the homepage."""

    return Page(state, [
        Header("Automated Chemistry Assistant"),

        "Welcome to your automated stoichiometry calculator.",

        Paragraph(
            "Determine limiting reactants, theoretical yields, "
            "percent yields, remaining reactant masses, and "
            "reaction heat."
        ),

        Header("How It Works"),

        "1. Enter a balanced chemical equation.",
        "2. Enter the starting masses of your reactants.",
        "3. Select your product and enter its harvested mass.",
        "4. Enter the enthalpy change of the reaction.",
        "5. Review your calculated results.",

        Header("Get Started"),

        Button("Start a New Reaction", "reaction_setup"),

        Button("View Reaction History", "history")
    ])


@route
def reaction_setup(state: State) -> Page:
    """Allow the user to enter a chemical reaction."""

    return Page(state, [
        Header("Reaction Setup"),

        "Enter your balanced chemical equation.",

        Paragraph(
            "Example: 2 H2 + O2 -> 2 H2O"
        ),

        "Chemical Equation:",
        TextBox("equation", state.equation),

        Button("Submit Equation", "parse_reaction"),

        state.error_message,

        *create_navigation()
    ])


@route
def parse_reaction(state: State, equation: str) -> Page:
    """Parse the equation and save its reactants and products."""

    state.equation = equation.strip()
    state.error_message = ""

    try:
        reactants, products = parse_equation(state.equation)

        state.reactants = reactants
        state.products = products

        state.selected_product = products[0].formula

        state.harvested_mass_g = 0.0
        state.delta_h = 0.0
        state.results = {}
        state.result_summary = ""

        return reactant_inputs(state)

    except Exception as error:
        state.error_message = str(error)
        return reaction_setup(state)


@route
def reactant_inputs(state: State) -> Page:
    """Display the reactant mass input page."""

    return Page(state, [
        Header("Reactant Starting Masses"),

        "Enter the starting mass of every reactant in grams.",

        Paragraph(
            "Use one line per reactant in the format Formula=Mass."
        ),

        Paragraph(
            "Example:\nH2=4.0\nO2=32.0"
        ),

        TextArea(
            "mass_text",
            create_mass_template(state.reactants),
            rows=6
        ),

        Button("Save Reactant Masses", "save_masses"),

        state.error_message,

        *create_navigation()
    ])


@route
def save_masses(state: State, mass_text: str) -> Page:
    """Save the starting masses of all reactants."""

    state.error_message = ""

    try:
        save_reactant_masses(state.reactants, mass_text)

        return product_inputs(state)

    except ValueError as error:
        state.error_message = str(error)
        return reactant_inputs(state)


@route
def product_inputs(state: State) -> Page:
    """Allow the user to select a product."""

    if not state.products:
        return Page(state, [
            Header("No Reaction Found"),
            Button("Enter a Reaction", "reaction_setup")
        ])

    product_options = []

    for compound in state.products:
        product_options.append(compound.formula)

    return Page(state, [
        Header("Product Information"),

        "Select the product you harvested.",

        SelectBox(
            "selected_product",
            product_options,
            state.selected_product
        ),

        "Enter the harvested product mass in grams:",

        TextBox("harvested_mass", "0.0"),

        Button("Save Product Information", "save_product"),

        state.error_message,

        *create_navigation()
    ])


@route
def save_product(
    state: State,
    selected_product: str,
    harvested_mass: str
) -> Page:
    """Save the selected product and harvested mass."""

    state.error_message = ""

    try:
        mass = float(harvested_mass)

        if mass < 0:
            raise ValueError(
                "Harvested mass cannot be negative."
            )

        state.selected_product = selected_product
        state.harvested_mass_g = mass

        return conditions(state)

    except ValueError:
        state.error_message = (
            "Enter a valid non-negative harvested mass in grams."
        )

        return product_inputs(state)


@route
def conditions(state: State) -> Page:
    """Collect the enthalpy change of the reaction."""

    return Page(state, [
        Header("Reaction Conditions"),

        Paragraph(
            "Enter ΔH in kJ per mole of reaction AS WRITTEN "
            "in your balanced chemical equation."
        ),

        Paragraph(
            "Negative ΔH = Exothermic (releases heat)."
        ),

        Paragraph(
            "Positive ΔH = Endothermic (absorbs heat)."
        ),

        Paragraph(
            "Example: Enter -100 for a reaction with "
            "ΔH = -100 kJ/mol of reaction."
        ),

        "Enthalpy Change (kJ/mol of reaction):",

        TextBox("delta_h_text", "0.0"),

        Button("Calculate Reaction", "calculate"),

        state.error_message,

        *create_navigation()
    ])


@route
def calculate(state: State, delta_h_text: str) -> Page:
    """Perform all chemistry calculations."""

    state.error_message = ""

    try:
        delta_h = float(delta_h_text)

        state.delta_h = delta_h

        results = calculate_stoichiometry(
            state.reactants,
            state.products,
            state.selected_product,
            state.harvested_mass_g,
            state.delta_h
        )

        state.results = results

        state.result_summary = (
            "Limiting Reactant: "
            + results["limiting_reactant"]
            + "\nTheoretical Yield: "
            + format(results["theoretical_yield"], ".4f")
            + " g\nHarvested Mass: "
            + format(results["harvested_mass"], ".4f")
            + " g\nPercent Yield: "
            + format(results["percent_yield"], ".2f")
            + "%\nReaction Type: "
            + results["heat_type"]
            + "\nHeat per Mole of Product: "
            + format(results["heat_per_mole"], ".4f")
            + " kJ/mol"
        )

        record = ReactionRecord(
            state.equation,
            state.selected_product,
            results["theoretical_yield"],
            results["harvested_mass"],
            results["percent_yield"]
        )

        state.history.append(record)

        return results_page(state)

    except ValueError as error:
        state.error_message = (
            "Calculation error: " + str(error)
        )

        return conditions(state)


@route
def results_page(state: State) -> Page:
    """Display the primary calculation results."""

    return Page(state, [
        Header("Reaction Results"),

        Header("Summary"),

        state.result_summary,

        Paragraph(
            "For a detailed explanation of the calculations, "
            "visit the reaction breakdown page."
        ),

        Button("Detailed Breakdown", "breakdown"),

        Button("New Reaction", "reaction_setup"),

        Button("Reaction History", "history"),

        *create_navigation()
    ])


@route
def breakdown(state: State) -> Page:
    """Display the detailed reactant and product calculations."""

    if not state.results:
        return Page(state, [
            Header("No Results Available"),
            Button("Start a Reaction", "reaction_setup")
        ])

    content = [
        Header("Detailed Reaction Breakdown"),

        Paragraph("Balanced Equation: " + state.equation),

        Header("Reactant Information")
    ]

    # This loop processes every reactant class instance.
    for compound in state.reactants:
        content.append(
            Paragraph(
                compound.formula
                + "\nStarting Mass: "
                + format(compound.starting_mass_g, ".4f")
                + " g\nAvailable Moles: "
                + format(compound.available_moles, ".4f")
                + " mol\nConsumed Moles: "
                + format(compound.consumed_moles, ".4f")
                + " mol\nRemaining Mass: "
                + format(compound.remaining_mass_g, ".4f")
                + " g"
            )
        )

    content.append(Header("Product Information"))

    for compound in state.products:
        content.append(
            Paragraph(
                compound.formula
                + "\nTheoretical Yield: "
                + format(compound.theoretical_mass_g, ".4f")
                + " g"
            )
        )

    content.append(Header("Reaction Heat"))

    content.append(
        Paragraph(
            "Enthalpy Change: "
            + str(state.delta_h)
            + " kJ/mol of reaction"
        )
    )

    content.append(
        Paragraph(
            "Reaction Type: "
            + state.results["heat_type"]
        )
    )

    content.append(
        Paragraph(
            "Heat per Mole of Selected Product: "
            + format(state.results["heat_per_mole"], ".4f")
            + " kJ/mol"
        )
    )

    content.append(
        Paragraph(
            "Total Heat for the Theoretical Reaction Amount: "
            + format(state.results["total_heat"], ".4f")
            + " kJ"
        )
    )

    content.append(
        Button("Return to Results", "results_page")
    )

    content.extend(create_navigation())

    return Page(state, content)


@route
def history(state: State) -> Page:
    """Display previously calculated reactions."""

    content = [
        Header("Reaction History")
    ]

    if len(state.history) == 0:
        content.append("No previous calculations.")
    else:
        # Each saved record is an instance of ReactionRecord.
        for record in state.history:
            content.append(
                Paragraph(
                    record.equation
                    + "\nSelected Product: "
                    + record.product
                    + "\nTheoretical Yield: "
                    + format(record.theoretical_yield, ".4f")
                    + " g\nHarvested Mass: "
                    + format(record.harvested_mass, ".4f")
                    + " g\nPercent Yield: "
                    + format(record.percent_yield, ".2f")
                    + "%"
                )
            )

    content.append(
        Button("Start Another Reaction", "reaction_setup")
    )

    content.extend(create_navigation())

    return Page(state, content)


@route
def reset(state: State) -> Page:
    """Clear the current reaction and return to the homepage."""

    state.equation = ""
    state.reactants = []
    state.products = []

    state.selected_product = ""
    state.harvested_mass_g = 0.0
    state.delta_h = 0.0

    state.results = {}
    state.result_summary = ""
    state.error_message = ""

    return index(state)


if __name__ == "__main__":
    start_server(State())
