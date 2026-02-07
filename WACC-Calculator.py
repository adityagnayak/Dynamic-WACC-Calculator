import streamlit as st
import pandas as pd

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dynamic WACC Calculator",
    page_icon="📊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# CUSTOM CSS FOR FORMULA HIGHLIGHTING
# -----------------------------------------------------------------------------
# We use custom CSS to allow smooth transitions for the "light up" effect.
st.markdown("""
    <style>
    .formula-container {
        font-family: 'Courier New', Courier, monospace;
        font-size: 24px;
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid #d6d6d8;
    }
    .term {
        transition: all 0.3s ease;
        padding: 0 5px;
        border-radius: 4px;
    }
    .term-inactive {
        color: #888888;
        font-weight: normal;
    }
    .term-active {
        color: #0f9d58; /* Green */
        font-weight: bold;
        background-color: #e6f4ea;
        box-shadow: 0 0 5px rgba(15, 157, 88, 0.2);
    }
    .operator {
        color: #333;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# HEADER
# -----------------------------------------------------------------------------
st.title("📊 Corporate WACC Modeler")
st.markdown("""
This tool calculates the **Weighted Average Cost of Capital (WACC)**. 
Inputs are dynamic—add as many debt sources as needed. 
The formula below **lights up** as you populate the relevant data.
""")

st.divider()

# -----------------------------------------------------------------------------
# INPUT SECTION (Sidebar & Main Columns)
# -----------------------------------------------------------------------------

# Use columns for layout
col1, col2, col3 = st.columns([1, 1, 1])

# --- 1. CORPORATE TAX ---
with col1:
    st.subheader("1. Corporate Tax")
    tax_rate_input = st.number_input(
        "Corporate Tax Rate (%)", 
        min_value=0.0, max_value=100.0, value=0.0, step=0.1,
        help="The effective tax rate paid by the firm."
    )
    tax_rate = tax_rate_input / 100.0

# --- 2. EQUITY CAPITAL ---
with col2:
    st.subheader("2. Equity Capital")
    
    # Local Equity
    st.markdown("**Local Equity**")
    le_amount = st.number_input("Local Equity Amount ($)", min_value=0.0, value=0.0, step=1000.0)
    le_cost = st.number_input("Cost of Local Equity (%)", min_value=0.0, value=0.0, step=0.1) / 100.0
    
    # Foreign Equity
    st.markdown("**Foreign Equity**")
    fe_amount = st.number_input("Foreign Equity Amount ($)", min_value=0.0, value=0.0, step=1000.0)
    fe_cost = st.number_input("Cost of Foreign Equity (%)", min_value=0.0, value=0.0, step=0.1) / 100.0

    # Equity Calculations
    total_equity = le_amount + fe_amount
    
    # Calculate Weighted Average Cost of Equity (Re)
    if total_equity > 0:
        cost_of_equity = ((le_amount * le_cost) + (fe_amount * fe_cost)) / total_equity
    else:
        cost_of_equity = 0.0

# --- 3. DEBT CAPITAL (Dynamic) ---
with col3:
    st.subheader("3. Debt Capital")
    
    # Local Debt Dynamic Inputs
    st.markdown("**Local Debt Sources**")
    num_local_debt = st.number_input("Number of Local Debt Sources", min_value=0, value=1, step=1)
    
    local_debt_data = []
    if num_local_debt > 0:
        with st.expander("Enter Local Debt Details", expanded=True):
            for i in range(int(num_local_debt)):
                c_a, c_b = st.columns(2)
                amt = c_a.number_input(f"L-Debt {i+1} Amount ($)", min_value=0.0, key=f"ld_amt_{i}")
                rate = c_b.number_input(f"L-Debt {i+1} Rate (%)", min_value=0.0, key=f"ld_rate_{i}") / 100.0
                local_debt_data.append({"Amount": amt, "Rate": rate})

    # Foreign Debt Dynamic Inputs
    st.markdown("**Foreign Debt Sources**")
    num_foreign_debt = st.number_input("Number of Foreign Debt Sources", min_value=0, value=0, step=1)
    
    foreign_debt_data = []
    if num_foreign_debt > 0:
        with st.expander("Enter Foreign Debt Details", expanded=True):
            for i in range(int(num_foreign_debt)):
                c_a, c_b = st.columns(2)
                amt = c_a.number_input(f"F-Debt {i+1} Amount ($)", min_value=0.0, key=f"fd_amt_{i}")
                rate = c_b.number_input(f"F-Debt {i+1} Rate (%)", min_value=0.0, key=f"fd_rate_{i}") / 100.0
                foreign_debt_data.append({"Amount": amt, "Rate": rate})

    # Debt Calculations
    all_debt = local_debt_data + foreign_debt_data
    total_debt = sum(d["Amount"] for d in all_debt)
    
    # Calculate Weighted Average Cost of Debt (Rd)
    if total_debt > 0:
        weighted_interest = sum(d["Amount"] * d["Rate"] for d in all_debt)
        cost_of_debt = weighted_interest / total_debt
    else:
        cost_of_debt = 0.0

# -----------------------------------------------------------------------------
# MAIN CALCULATION & FORMULA LOGIC
# -----------------------------------------------------------------------------

total_value = total_equity + total_debt

# Avoid division by zero
if total_value > 0:
    wacc = ((total_equity / total_value) * cost_of_equity) + \
           ((total_debt / total_value) * cost_of_debt * (1 - tax_rate))
    
    weight_equity = total_equity / total_value
    weight_debt = total_debt / total_value
else:
    wacc = 0.0
    weight_equity = 0.0
    weight_debt = 0.0

# -----------------------------------------------------------------------------
# DYNAMIC UI: INTERACTIVE FORMULA
# -----------------------------------------------------------------------------
# Determine active states for highlighting
# We define a helper function to determine CSS class based on value presence
def get_class(value, threshold=0):
    return "term-active" if value > threshold else "term-inactive"

# Logic for specific terms:
# E  -> Active if Total Equity > 0
# V  -> Active if Total Value > 0
# Re -> Active if Cost of Equity > 0
# D  -> Active if Total Debt > 0
# Rd -> Active if Cost of Debt > 0
# T  -> Active if Tax Rate is entered (checking > 0 for visualization, 
#       but practically checks if user interacted. Here we use value > 0).

class_E = get_class(total_equity)
class_V = get_class(total_value)
class_Re = get_class(cost_of_equity)
class_D = get_class(total_debt)
class_Rd = get_class(cost_of_debt)
class_T = get_class(tax_rate_input) # Use input to detect 0 input vs empty

st.divider()
st.subheader("Interactive Formula View")

# We build the HTML formula manually to allow granular control over styling
# Formula: WACC = (E/V * Re) + (D/V * Rd * (1 - T))

html_formula = f"""
<div class="formula-container">
    WACC = 
    [ 
    <span class="term {class_E}" title="Market Value of Equity">${total_equity:,.0f} (E)</span> 
    <span class="operator">/</span> 
    <span class="term {class_V}" title="Total Value (Equity + Debt)">${total_value:,.0f} (V)</span> 
    <span class="operator">×</span> 
    <span class="term {class_Re}" title="Cost of Equity">{cost_of_equity:.2%} (Re)</span> 
    ]
    <span class="operator">+</span>
    [ 
    <span class="term {class_D}" title="Market Value of Debt">${total_debt:,.0f} (D)</span> 
    <span class="operator">/</span> 
    <span class="term {class_V}" title="Total Value (Equity + Debt)">${total_value:,.0f} (V)</span> 
    <span class="operator">×</span> 
    <span class="term {class_Rd}" title="Cost of Debt">{cost_of_debt:.2%} (Rd)</span> 
    <span class="operator">×</span> 
    (1 - <span class="term {class_T}" title="Corporate Tax Rate">{tax_rate:.2%} (T)</span>) 
    ]
</div>
"""

st.markdown(html_formula, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# RESULTS DISPLAY
# -----------------------------------------------------------------------------
st.subheader("Calculation Results")

res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.metric(label="Total Equity (E)", value=f"${total_equity:,.2f}")
    st.metric(label="Weighted Cost of Equity (Re)", value=f"{cost_of_equity:.2%}")

with res_col2:
    st.metric(label="Total Debt (D)", value=f"${total_debt:,.2f}")
    st.metric(label="Weighted Cost of Debt (Rd)", value=f"{cost_of_debt:.2%}")

with res_col3:
    st.metric(label="WACC", value=f"{wacc:.2%}", delta_color="normal")
    st.metric(label="Total Firm Value (V)", value=f"${total_value:,.2f}")

# -----------------------------------------------------------------------------
# CODE DISPLAY (Requirement: Display the actual Python logic)
# -----------------------------------------------------------------------------
with st.expander("View Calculation Logic (Python Code)"):
    st.code(f"""
# 1. Calculate Total Equity and Weighted Cost of Equity (Re)
total_equity = {le_amount} + {fe_amount}
# Re = ( (Local_Eq * Local_Cost) + (Foreign_Eq * Foreign_Cost) ) / Total_Equity
cost_of_equity = (({le_amount} * {le_cost}) + ({fe_amount} * {fe_cost})) / {total_equity if total_equity else 1}

# 2. Calculate Total Debt and Weighted Cost of Debt (Rd)
total_debt = {total_debt}
# Rd = (Sum of (Debt_Source_Amount * Debt_Source_Rate)) / Total_Debt
cost_of_debt = {cost_of_debt} 

# 3. Calculate Firm Value (V)
total_value = total_equity + total_debt

# 4. WACC Formula
# WACC = (E/V * Re) + (D/V * Rd * (1 - T))
tax_factor = (1 - {tax_rate})
equity_part = (total_equity / total_value) * cost_of_equity
debt_part = (total_debt / total_value) * cost_of_debt * tax_factor

wacc = equity_part + debt_part
    """, language="python")
