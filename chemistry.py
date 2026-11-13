
"""
chemistry.py

Contains the chemistry calculations for the automated
chemistry assistant.

Requires the Chempy package.
"""

import re
from dataclasses import dataclass

from chempy import Substance


@dataclass
class Compound:
    """Stores information about an individual chemical compound."""

    formula: str
    coefficient: int
    molar_mass: float
    starting_mass_g: float = 0.0
    available_moles: float = 0.0
    consumed_moles: float = 0.0
    remaining_mass_g: float = 0.0
    theoretical_mass_g: float = 0.0


def get_molar_mass(formula: str) -> float:
    """Use Chempy to calculate a compound's molar mass."""

    substance = Substance.from_formula(formula)
    return float(substance.mass)


def parse_side(side: str) -> list[Compound]:
    """Parse one side of a chemical equation into compounds."""

    compounds = []
    terms = side.split(" + ")

    for term in terms:
        term = term.strip()

        # A coefficient is optional. If absent, it is one.
        match = re.fullmatch(
            r"(\d+)?\s*([A-Za-z][A-Za-z0-9()]*)",
            term
        )

        if match is None:
            raise ValueError(
                "Invalid compound: " + term
            )

        coefficient_text = match.group(1)
        formula = match.group(2)

        if coefficient_text is None:
            coefficient = 1
        else:
            coefficient = int(coefficient_text)

        if coefficient <= 0:
            raise ValueError("Coefficients must be positive.")

        if any(item.formula == formula for item in compounds):
            raise ValueError(
                "Do not repeat a compound on the same side."
            )

        molar_mass = get_molar_mass(formula)

        if molar_mass <= 0:
            raise ValueError("Invalid molecular weight.")

        compounds.append(
            Compound(formula, coefficient, molar_mass)
        )

    return compounds


def is_balanced(
    reactants: list[Compound],
    products: list[Compound]
) -> bool:
    """Check whether both sides contain equal numbers of atoms."""

    reactant_atoms = {}
    product_atoms = {}

    for compound in reactants:
        composition = Substance.from_formula(
            compound.formula
        ).composition

        for element, amount in composition.items():
            reactant_atoms[element] = (
                reactant_atoms.get(element, 0)
                + amount * compound.coefficient
            )

    for compound in products:
        composition = Substance.from_formula(
            compound.formula
        ).composition

        for element, amount in composition.items():
            product_atoms[element] = (
                product_atoms.get(element, 0)
                + amount * compound.coefficient
            )

    return reactant_atoms == product_atoms


def parse_equation(
    equation: str
) -> tuple[list[Compound], list[Compound]]:
    """
    Parse and validate a complete chemical equation.

    Supported format:
    2 H2 + O2 -> 2 H2O

    This version supports neutral molecular formulas and
    integer stoichiometric coefficients.
    """

    equation = equation.replace("→", "->")

    if equation.count("->") != 1:
        raise ValueError(
            "Use exactly one reaction arrow (->)."
        )

    left_side, right_side = equation.split("->")

    reactants = parse_side(left_side)
    products = parse_side(right_side)

    if len(reactants) == 0 or len(products) == 0:
        raise ValueError(
            "Your equation needs reactants and products."
        )

    if not is_balanced(reactants, products):
        raise ValueError(
            "Your chemical equation is not balanced."
        )

    return reactants, products


def calculate_stoichiometry(
    reactants: list[Compound],
    products: list[Compound],
    selected_product: str,
    harvested_mass_g: float,
    delta_h: float
) -> dict:
    """
    Calculate limiting reagent, theoretical yield, actual yield,
    excess reactants, and reaction heat.

    delta_h is kJ per mole of reaction as written.
    """

    if harvested_mass_g < 0:
        raise ValueError("Harvested mass cannot be negative.")

    # Convert each starting reactant mass into moles.
    for compound in reactants:
        if compound.starting_mass_g <= 0:
            raise ValueError(
                "Every reactant needs a positive starting mass."
            )

        compound.available_moles = (
            compound.starting_mass_g / compound.molar_mass
        )

        compound.consumed_moles = 0.0
        compound.remaining_mass_g = 0.0

    # Find how many times the complete reaction can occur.
    reaction_amounts = []

    for compound in reactants:
        possible_reactions = (
            compound.available_moles / compound.coefficient
        )

        reaction_amounts.append(possible_reactions)

    reaction_extent = min(reaction_amounts)

    limiting_index = reaction_amounts.index(reaction_extent)
    limiting_reactant = reactants[limiting_index]

    # Calculate the amount of each reactant consumed.
    for compound in reactants:
        compound.consumed_moles = (
            reaction_extent * compound.coefficient
        )

        remaining_moles = (
            compound.available_moles - compound.consumed_moles
        )

        # Avoid tiny negative values caused by floating-point math.
        if abs(remaining_moles) < 1e-10:
            remaining_moles = 0.0

        compound.remaining_mass_g = (
            remaining_moles * compound.molar_mass
        )

    # Calculate the theoretical yield of every product.
    selected_compound = None

    for compound in products:
        theoretical_moles = (
            reaction_extent * compound.coefficient
        )

        compound.theoretical_mass_g = (
            theoretical_moles * compound.molar_mass
        )

        if compound.formula == selected_product:
            selected_compound = compound

    if selected_compound is None:
        raise ValueError("Selected product was not found.")

    theoretical_yield = selected_compound.theoretical_mass_g

    if theoretical_yield <= 0:
        raise ValueError("The theoretical yield must be positive.")

    percent_yield = (
        harvested_mass_g / theoretical_yield
    ) * 100

    # Delta H is expressed per mole of reaction as written.
    # Divide by the product coefficient to obtain kJ per
    # mole of that particular product.
    heat_per_mole_product = (
        delta_h / selected_compound.coefficient
    )

    total_heat = reaction_extent * delta_h

    if delta_h < 0:
        heat_type = "Exothermic"
    elif delta_h > 0:
        heat_type = "Endothermic"
    else:
        heat_type = "Thermoneutral"

    return {
        "limiting_reactant": limiting_reactant.formula,
        "reaction_extent": reaction_extent,
        "theoretical_yield": theoretical_yield,
        "harvested_mass": harvested_mass_g,
        "percent_yield": percent_yield,
        "heat_per_mole": heat_per_mole_product,
        "total_heat": total_heat,
        "heat_type": heat_type
    }
