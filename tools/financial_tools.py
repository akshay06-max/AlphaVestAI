"""Custom Python financial calculation tools — Module 10."""
import re
import json
import math
try:
    from langchain_core.tools import tool
except (ImportError, ModuleNotFoundError):
    from langchain.tools import tool
import pandas as pd


@tool
def calculate_cagr(begin_value: float, end_value: float, years: float) -> str:
    """Calculate Compound Annual Growth Rate (CAGR) as a percentage.
    Args: begin_value (starting value), end_value (ending value), years (number of years)."""
    if begin_value <= 0 or years <= 0:
        return "Error: begin_value and years must be positive numbers."
    cagr = ((end_value / begin_value) ** (1 / years) - 1) * 100
    return (
        f"📊 CAGR Result:\n"
        f"• Starting Value: {begin_value:,.2f}\n"
        f"• Ending Value: {end_value:,.2f}\n"
        f"• Period: {years} years\n"
        f"• **Compound Annual Growth Rate (CAGR): {round(cagr, 2)}%**"
    )


@tool
def calculate_growth_percentage(old_value: float, new_value: float) -> str:
    """Calculate percentage growth between two values (e.g. year-over-year or quarter-over-quarter revenue growth)."""
    if old_value == 0:
        return "Error: old_value cannot be zero."
    growth = ((new_value - old_value) / abs(old_value)) * 100
    direction = "Growth" if growth >= 0 else "Decline"
    return (
        f"📈 Growth Percentage:\n"
        f"• Base Value: {old_value:,.2f}\n"
        f"• New Value: {new_value:,.2f}\n"
        f"• **{direction}: {round(growth, 2)}%**"
    )


@tool
def calculate_roi(investment: float, current_value: float) -> str:
    """Calculate Return on Investment (ROI) as a percentage."""
    if investment == 0:
        return "Error: investment cannot be zero."
    roi = ((current_value - investment) / investment) * 100
    net_profit = current_value - investment
    return (
        f"💰 Return on Investment (ROI):\n"
        f"• Initial Investment: ${investment:,.2f}\n"
        f"• Current/Final Value: ${current_value:,.2f}\n"
        f"• Net Gain: ${net_profit:,.2f}\n"
        f"• **ROI: {round(roi, 2)}%**"
    )


@tool
def build_comparison_table(companies_json: str) -> str:
    """Build a formatted markdown comparison table.
    Input must be a JSON string like:
    '{"Google": {"Revenue ($B)": 307, "Growth": "12%", "P/E": 26}, "Microsoft": {"Revenue ($B)": 245, "Growth": "16%", "P/E": 34}}'
    """
    try:
        data = json.loads(companies_json)
        df = pd.DataFrame(data).T
        return df.to_markdown()
    except Exception as e:
        return f"Error building table: {e}"


@tool
def python_financial_calculator(expression: str) -> str:
    """Safely evaluate Python financial math expressions (e.g., margins, ratios, DCF valuations)."""
    try:
        # Safe math evaluation environment
        allowed_names = {
            "math": math,
            "abs": abs,
            "round": round,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
        }
        clean_expr = expression.replace("$", "").replace("%", "/100")
        result = eval(clean_expr, {"__builtins__": {}}, allowed_names)
        return f"Calculated Result: {result}"
    except Exception as e:
        return f"Calculation error for '{expression}': {e}"


financial_tools = [
    calculate_cagr,
    calculate_growth_percentage,
    calculate_roi,
    build_comparison_table,
    python_financial_calculator,
]


def run_financial_calculation_query(query: str) -> str:
    """Direct helper to extract parameters and run financial calculations from user queries."""
    # Check for CAGR
    numbers = [float(n.replace(",", "")) for n in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", query)]
    
    if "cagr" in query.lower():
        if len(numbers) >= 3:
            return calculate_cagr.func(numbers[0], numbers[1], numbers[2])
        elif len(numbers) == 2:
            return calculate_cagr.func(numbers[0], numbers[1], 5.0)  # default 5 years
        return "Please specify starting value, ending value, and years. Example: 'Calculate CAGR from 100 to 250 over 5 years'"
    
    if "roi" in query.lower():
        if len(numbers) >= 2:
            return calculate_roi.func(numbers[0], numbers[1])
        return "Please specify initial investment and current value. Example: 'Calculate ROI for 50000 to 75000'"
        
    if any(k in query.lower() for k in ["growth percentage", "annual growth", "growth rate"]):
        if len(numbers) >= 2:
            return calculate_growth_percentage.func(numbers[0], numbers[1])
        return "Please provide old and new values. Example: 'Calculate annual growth from 200M to 280M'"
        
    if "table" in query.lower() or "comparison table" in query.lower():
        sample_data = {
            "Google (Alphabet)": {"Revenue ($B)": "307.4", "YoY Growth": "+13%", "Net Margin": "26.8%", "P/E Ratio": "24.5"},
            "Microsoft": {"Revenue ($B)": "245.1", "YoY Growth": "+16%", "Net Margin": "35.2%", "P/E Ratio": "32.1"},
            "Amazon": {"Revenue ($B)": "574.8", "YoY Growth": "+11%", "Net Margin": "7.1%", "P/E Ratio": "42.0"},
            "Apple": {"Revenue ($B)": "383.3", "YoY Growth": "+2%", "Net Margin": "25.3%", "P/E Ratio": "33.2"},
        }
        return build_comparison_table.func(json.dumps(sample_data))
        
    # Python calc fallback
    return python_financial_calculator.func(query)
