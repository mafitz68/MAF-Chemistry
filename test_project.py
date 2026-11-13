
"""
test_project.py

Unit tests for the chemistry assistant.

Run using:
pytest test_project.py
"""

import os

# Prevent Drafter from starting a website during testing.
os.environ["DRAFTER_SKIP"] = "1"

import pytest

from chemistry import (
    parse_equation,
    calculate_stoichiometry
)

from main import (
    State,
    index,
    reaction_setup,
    parse_reaction,
    reactant_inputs,
    save_masses,
    product_inputs,
    save_product,
    conditions,
    calculate,
    results_page,
    breakdown,
    history,
    reset
)


def create_ready_state() -> State:
    """Create a state with a reaction and all required inputs."""

    state = State()

    parse_reaction(
        state,
        "2 H2 + O2 -> 2 H2O"
    )

    save_masses(
        state,
        "H2=4.032\nO2=63.996"
    )

    save_product(
        state,
        "H2O",
        "30"
    )

    return state


# CHEMISTRY TESTS


def test_parse_balanced_equation():
    """Check that a balanced equation is parsed correctly."""

    reactants, products = parse_equation(
        "2 H2 + O2 -> 2 H2O"
    )

    assert len(reactants) == 2
    assert len(products) == 1

    assert reactants[0].formula == "H2"
    assert products[0].formula == "H2O"


def test_parse_unbalanced_equation():
    """An unbalanced equation should be rejected."""

    with pytest.raises(ValueError):
        parse_equation("H2 + O2 -> H2O")


def test_parse_equation_with_parentheses():
    """Check that formulas containing parentheses work."""

    reactants, products = parse_equation(
        "Ca(OH)2 + 2 HCl -> CaCl2 + 2 H2O"
    )

    assert len(reactants) == 2
    assert len(products) == 2


def test_limiting_reactant():
    """Check that the correct limiting reactant is identified."""

    state = create_ready_state()

    results = calculate_stoichiometry(
        state.reactants,
        state.products,
        "H2O",
        30.0,
        -483.6
    )

    assert results["limiting_reactant"] == "H2"


def test_theoretical_yield():
    """Check the calculated theoretical product mass."""

    state = create_ready_state()

    results = calculate_stoichiometry(
        state.reactants,
        state.products,
        "H2O",
        30.0,
        -483.6
    )

    assert results["theoretical_yield"] == pytest.approx(
        36.03,
        rel=0.001
    )


def test_percent_yield():
    """Check the percent yield calculation."""

    state = create_ready_state()

    results = calculate_stoichiometry(
        state.reactants,
        state.products,
        "H2O",
        30.0,
        -483.6
    )

    assert results["percent_yield"] == pytest.approx(
        83.26,
        rel=0.001
    )


def test_excess_reactant_mass():
    """Check the remaining mass of the excess reactant."""

    state = create_ready_state()

    calculate_stoichiometry(
        state.reactants,
        state.products,
        "H2O",
        30.0,
        -483.6
    )

    oxygen = state.reactants[1]

    assert oxygen.remaining_mass_g == pytest.approx(
        31.998,
        rel=0.001
    )


def test_reaction_heat():
    """Check the heat classification and heat per mole."""

    state = create_ready_state()

    results = calculate_stoichiometry(
        state.reactants,
        state.products,
        "H2O",
        30.0,
        -483.6
    )

    assert results["heat_type"] == "Exothermic"

    assert results["heat_per_mole"] == pytest.approx(
        -241.8
    )


def test_endothermic_reaction():
    """Check that a positive enthalpy is endothermic."""

    state = create_ready_state()

    results = calculate_stoichiometry(
        state.reactants,
        state.products,
        "H2O",
        30.0,
        483.6
    )

    assert results["heat_type"] == "Endothermic"


# WEBSITE ROUTE TESTS


def test_homepage_route():
    """Check that the homepage displays successfully."""

    assert index(State()) is not None


def test_reaction_setup_route():
    """Check that the reaction setup page displays."""

    assert reaction_setup(State()) is not None


def test_parse_reaction_route():
    """Check that the equation is saved to the state."""

    state = State()

    parse_reaction(
        state,
        "2 H2 + O2 -> 2 H2O"
    )

    assert state.equation == "2 H2 + O2 -> 2 H2O"
    assert len(state.reactants) == 2


def test_reactant_inputs_route():
    """Check that the reactant input page displays."""

    state = create_ready_state()

    assert reactant_inputs(state) is not None


def test_save_masses_route():
    """Check that reactant masses are saved."""

    state = State()

    parse_reaction(
        state,
        "2 H2 + O2 -> 2 H2O"
    )

    save_masses(
        state,
        "H2=4.032\nO2=63.996"
    )

    assert state.reactants[0].starting_mass_g == 4.032
    assert state.reactants[1].starting_mass_g == 63.996


def test_product_inputs_route():
    """Check that the product selection page displays."""

    state = create_ready_state()

    assert product_inputs(state) is not None


def test_save_product_route():
    """Check that product information is saved."""

    state = create_ready_state()

    assert state.selected_product == "H2O"
    assert state.harvested_mass_g == 30.0


def test_conditions_route():
    """Check that the reaction conditions page displays."""

    state = create_ready_state()

    assert conditions(state) is not None


def test_calculate_route():
    """Check that the calculation route produces results."""

    state = create_ready_state()

    calculate(state, "-483.6")

    assert state.results["limiting_reactant"] == "H2"
    assert state.results["heat_type"] == "Exothermic"


def test_results_route():
    """Check that the results page displays."""

    state = create_ready_state()

    calculate(state, "-483.6")

    assert results_page(state) is not None


def test_breakdown_route():
    """Check that the detailed breakdown page displays."""

    state = create_ready_state()

    calculate(state, "-483.6")

    assert breakdown(state) is not None


def test_history_route():
    """Check that completed reactions appear in history."""

    state = create_ready_state()

    calculate(state, "-483.6")

    assert len(state.history) == 1
    assert history(state) is not None


def test_reset_route():
    """Check that the current reaction is cleared."""

    state = create_ready_state()

    reset(state)

    assert state.equation == ""
    assert len(state.reactants) == 0
    assert len(state.products) == 0
    assert state.results == {}
