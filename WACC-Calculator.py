import streamlit as st
import pandas as pd
import yfinance as yf

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dynamic Multi-Currency WACC",
    page_icon="🌍",
    layout="wide"
)

# -----------------------------------------------------------------------------
# UTILITIES: FX RATE FETCHER
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)  # Cache data for 1 hour to prevent constant API calls
def get_fx_rate(source_curr, target_curr):
    """Fetches the exchange rate from Yahoo Finance."""
    if source_curr == target_curr:
        return 1.0
    
    # Standard Yahoo Finance tickers are often "EURUSD=X"
    ticker = f"{source_curr}{target_curr}=X"
    try:
        data = yf.Ticker(ticker)
        history = data.history(period="1d")
        if not history.empty:
            return history['Close'].iloc[-1]
        else:
            # Try reverse pair if direct fails
            ticker_rev = f"{target_curr}{source_curr}=X"
            data_rev = yf.Ticker(ticker_rev)
            history_rev = data_rev.history(period="1d")
            if not history_rev.empty:
                return 1.0 / history_rev['Close'].iloc[-1]
    except Exception:
        return 1.0
    return 1.0

# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    .formula-container {
        font-family: 'Courier New', Courier, monospace;
        font-size: 22px;
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid #dee2e6;
    }
    .term { transition: all 0.3s ease; padding: 2px 6px; border-radius: 4px; }
    .term-active { color: #198754; font-weight: bold; background-color: #d1e7dd; }
    .term-inactive { color: #adb5bd; }
    .operator { color: #495057; font-weight: bold; }
    .currency-badge {
        font-size: 0.8em;
        background-color: #e9ecef;
        padding: 2px 5px;
        border-radius: 4px;
        margin-left: 5px;
        color: #495057;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# HEADER & SETTINGS
# -----------------------------------------------------------------------------
col_head, col_set = st.columns([3, 1])
with col_head:
    st.title("🌍 Multi-Currency WACC Modeler")
    st.markdown("Calculate WACC with **dynamic foreign debt** conversion.")

with col_set:
    CURRENCY_OPTIONS = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CNY", "INR", "CHF"]
    home_currency = st.selectbox("🏠 Home (Reporting) Currency", CURRENCY_OPTIONS, index=0)

st.divider()

# -----------------------------------------------------------------------------
# INPUTS
# -----------------------------------------------------------------------------

col1, col2, col3 = st.columns([1, 1.2, 1.5])

# --- 1. TAX & EQUITY ---
with col1:
    st.subheader("1. Tax & Equity")
    tax_rate = st.number_input("Tax Rate (%)", 0.0, 100.0, 21.0, 0.1) / 100.0
    
    st.markdown(f"**Equity Capital ({home_currency})**")
    total_equity = st.number_input(f"Total Equity Value ({home_currency})", 0.0, value=1000000.0, step=10000.0)
    cost_of_equity = st.number_input("Cost of Equity (Re) %", 0.0, 100.0, 10.0, 0.1) / 100.0

# --- 2. LOCAL DEBT ---
with col2:
    st.subheader(f"2. Local Debt ({home_currency})")
    num_local = st.number_input("No. of Local Loans", 0, 10, 1)
    
    local_debt_total = 0.0
    local_weighted_rate_sum = 0.0
    
    if num_local > 0:
        with st.expander("Local Debt Details", expanded=True):
            for i in range(num_local):
                c1, c2 = st.columns(2)
                amt = c1.number_input(f"Loan {i+1} Amt ({home_currency})", 0.0, value=100000.0, key=f"ld_{i}")
                rate = c2.number_input(f"Loan {i+1} Rate (%)", 0.0, value=5.0, key=f"lr_{i}") / 100.0
                
                local_debt_total += amt
                local_weighted_rate_sum += (amt * rate)

# --- 3. FOREIGN DEBT (Dynamic FX) ---
with col3:
    st.subheader("3. Foreign Debt (FX)")
    num_foreign = st.number_input("No. of Foreign Loans", 0, 10, 1)
    
    foreign_debt_home_total = 0.0
    foreign_weighted_rate_sum = 0.0
    
    if num_foreign > 0:
        with st.expander("Foreign Debt Details & FX", expanded=True):
            for i in range(num_foreign):
                st.markdown(f"**Foreign Loan {i+1}**")
                r1, r2, r3, r4 = st.columns([1, 1, 1, 1])
                
                # Input: Currency
                f_curr = r1.selectbox(f"Curr", CURRENCY_OPTIONS, index=1, key=f"fc_{i}")
                
                # Fetch FX Rate
                fetched_rate = get_fx_rate(f_curr, home_currency)
                
                # Input: Amount in Foreign Currency
                f_amt = r2.number_input(f"Amt ({f_curr})", 0.0, value=100000.0, key=f"fa_{i}")
                
                # Input: FX Rate (Allow Override)
                fx_rate = r3.number_input(f"FX ({f_curr}/{home_currency})", value=float(fetched_rate), format="%.4f", key=f"fx_{i}")
                
                # Input: Interest Rate
                f_rate_pct = r4.number_input(f"Rate (%)", 0.0, value=4.0, key=f"fr_{i}") / 100.0
                
                # Calculation: Convert to Home Currency
                amt_home = f_amt * fx_rate
                foreign_debt_home_total += amt_home
                foreign_weighted_rate_sum += (amt_home * f_rate_pct)
                
                # Visual Feedback
                st.caption(f"↳ Value in {home_currency}: **{amt_home:,.0f}** (at {fx_rate:.4f})")

# -----------------------------------------------------------------------------
# CALCULATIONS
# -----------------------------------------------------------------------------

# Total Debt (in Home Currency)
total_debt = local_debt_total + foreign_debt_home_total

# Weighted Average Cost of Debt (Rd)
# We weight the interest rates by the Home Currency Value of the principal
total_weighted_interest = local_weighted_rate_sum + foreign_weighted_rate_sum

if total_debt > 0:
    cost_of_debt = total_weighted_interest / total_debt
else:
    cost_of_debt = 0.0

total_value = total_equity + total_debt

# WACC Calculation
if total_value > 0:
    wacc = ((total_equity / total_value) * cost_of_equity) + \
           ((total_debt / total_value) * cost_of_debt * (1 - tax_rate))
else:
    wacc = 0.0

# -----------------------------------------------------------------------------
# DYNAMIC FORMULA DISPLAY
# -----------------------------------------------------------------------------
def get_cls(val): return "term-active" if val > 0 else "term-inactive"

html_formula = f"""
<div class="formula-container">
    WACC = 
    [ 
    <span class="term {get_cls(total_equity)}" title="Equity Value">E</span> 
    <span class="operator">/</span> 
    <span class="term {get_cls(total_value)}" title="Total Value">V</span> 
    <span class="operator">×</span> 
    <span class="term {get_cls(cost_of_equity)}">Re</span> 
    ]
    <span class="operator">+</span>
    [ 
    <span class="term {get_cls(total_debt)}" title="Debt Value (Converted to Home Currency)">D</span> 
    <span class="operator">/</span> 
    <span class="term {get_cls(total_value)}" title="Total Value">V</span> 
    <span class="operator">×</span> 
    <span class="term {get_cls(cost_of_debt)}" title="Weighted Cost of Debt">Rd</span> 
    <span class="operator">×</span> 
    (1 - <span class="term {get_cls(tax_rate)}">T</span>) 
    ]
</div>
"""
st.markdown(html_formula, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# RESULTS
# -----------------------------------------------------------------------------
st.subheader("Calculation Results")
c_res1, c_res2, c_res3, c_res4 = st.columns(4)

with c_res1:
    st.metric("Total Equity (E)", f"{home_currency} {total_equity:,.0f}")
with c_res2:
    st.metric("Total Debt (D)", f"{home_currency} {total_debt:,.0f}", help="Sum of Local + Converted Foreign Debt")
with c_res3:
    st.metric("Weighted Cost of Debt (Rd)", f"{cost_of_debt:.2%}")
with c_res4:
    st.metric("WACC", f"{wacc:.2%}", delta="Final Metric")

# -----------------------------------------------------------------------------
# LOGIC DISCLOSURE
# -----------------------------------------------------------------------------
with st.expander("View Logic & Python Code"):
    st.code(f"""
# 1. Foreign Debt Conversion
# We iterate through foreign loans and convert them to {home_currency}
# Formula: Amount_Home = Amount_Foreign * FX_Rate
total_debt_home = {local_debt_total} (Local) + {foreign_debt_home_total} (Foreign Converted)

# 2. Weighted Cost of Debt (Rd)
# We weight the interest rate of each loan by its value in {home_currency}
weighted_interest = {total_weighted_interest:,.2f}
total_debt = {total_debt:,.2f}
rd = weighted_interest / total_debt  # Result: {cost_of_debt:.2%}

# 3. WACC Calculation
equity_weight = {total_equity} / {total_value}
debt_weight = {total_debt} / {total_value}
tax_shield = (1 - {tax_rate})

wacc = (equity_weight * {cost_of_equity}) + (debt_weight * {cost_of_debt} * tax_shield)
    """, language="python")
