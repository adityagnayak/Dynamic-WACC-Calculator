import streamlit as st
import pandas as pd
import yfinance as yf
from typing import Tuple, Dict, List

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Global WACC Calculator",
    page_icon="🌐",
    layout="wide"
)

# -----------------------------------------------------------------------------
# UTILITIES: FX RATE FETCHER (FIXED & IMPROVED)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def get_fx_rate(home_curr: str, foreign_curr: str) -> float:
    """
    Fetches exchange rate: How many HOME currency units per 1 FOREIGN currency unit.
    Example: Home=USD, Foreign=EUR -> Returns ~1.05 (meaning 1 EUR = 1.05 USD)
    
    This allows simple conversion: foreign_amount * fx_rate = home_amount
    """
    if home_curr == foreign_curr:
        return 1.0
    
    # Try direct pair: FOREIGN/HOME (e.g., EURUSD=X gives USD per EUR)
    ticker = f"{foreign_curr}{home_curr}=X"
    try:
        data = yf.Ticker(ticker)
        history = data.history(period="1d", timeout=10)
        if not history.empty and len(history) > 0:
            rate = history['Close'].iloc[-1]
            if rate > 0:  # Validate the rate is positive
                return float(rate)
    except Exception as e:
        pass
    
    # Try reverse pair and invert
    ticker_rev = f"{home_curr}{foreign_curr}=X"
    try:
        data_rev = yf.Ticker(ticker_rev)
        history_rev = data_rev.history(period="1d", timeout=10)
        if not history_rev.empty and len(history_rev) > 0:
            rate_rev = history_rev['Close'].iloc[-1]
            if rate_rev > 0:  # Validate before inverting
                inverted = 1.0 / rate_rev
                return float(inverted)
    except Exception as e:
        pass
    
    # If both fail, show detailed warning
    st.warning(f"⚠️ Could not fetch FX rate for {foreign_curr}/{home_curr}. Please enter rate manually.")
    return 1.0


@st.cache_data(ttl=3600)
def get_all_fx_rates(home_curr: str, foreign_currencies: List[str]) -> Dict[str, float]:
    """
    Batch fetch all FX rates to reduce API calls.
    Returns dict mapping foreign_currency -> exchange_rate
    """
    rates = {}
    unique_currencies = set(foreign_currencies) - {home_curr}
    
    for foreign in unique_currencies:
        rates[foreign] = get_fx_rate(home_curr, foreign)
    
    return rates


# -----------------------------------------------------------------------------
# CAPITAL SOURCE RENDERING (REFACTORED - DRY PRINCIPLE)
# -----------------------------------------------------------------------------
def render_capital_sources(
    source_type: str,
    home_currency: str,
    currency_options: List[str],
    default_num: int = 0,
    default_cost: float = 10.0,
    cost_label: str = "Cost"
) -> Tuple[float, float, pd.DataFrame]:
    """
    Unified function for rendering equity/debt capital sources.
    
    Returns:
        - total_value: Total value in home currency
        - total_weighted_cost: Sum of (value * cost) for weighted average
        - details_df: DataFrame with breakdown of all sources
    """
    st.subheader(f"{source_type} Capital Sources")
    
    num_sources = st.number_input(
        f"Number of {source_type} Sources",
        min_value=0,
        max_value=20,
        value=default_num,
        key=f"num_{source_type.lower().replace(' ', '_')}"
    )
    
    total_value = 0.0
    total_weighted_cost = 0.0
    details = []
    
    if num_sources > 0:
        with st.expander(f"Enter {source_type} Details", expanded=True):
            for i in range(num_sources):
                st.markdown(f"**{source_type} Source {i+1}**")
                
                col1, col2, col3, col4 = st.columns([1, 1.2, 1.2, 1])
                
                # Currency selection
                source_curr = col1.selectbox(
                    "Currency",
                    currency_options,
                    index=0 if i == 0 else 1,
                    key=f"{source_type.lower()}_{i}_curr"
                )
                
                # Amount input
                raw_amount = col2.number_input(
                    f"Amount ({source_curr})",
                    min_value=0.0,
                    value=100000.0,
                    step=1000.0,
                    format="%.2f",
                    key=f"{source_type.lower()}_{i}_amt"
                )
                
                # FX Rate (only if different currency)
                if source_curr != home_currency:
                    # Force fresh FX rate fetch when currency changes
                    live_rate = get_fx_rate(home_currency, source_curr)
                    
                    # Create a unique key that forces widget refresh on currency change
                    # This key changes whenever either currency changes
                    fx_input_key = f"{source_type.lower()}_{i}_fx_{home_currency}_{source_curr}"
                    
                    # Check if currency changed and force value update
                    prev_key = f"{source_type.lower()}_{i}_prev_curr"
                    if prev_key not in st.session_state:
                        st.session_state[prev_key] = source_curr
                    
                    # If currency changed, clear the old FX value from session state
                    if st.session_state[prev_key] != source_curr:
                        st.session_state[prev_key] = source_curr
                        # Force the widget to use the new live_rate by removing old value
                        if fx_input_key in st.session_state:
                            del st.session_state[fx_input_key]
                    
                    fx_rate = col3.number_input(
                        f"1 {source_curr} = ? {home_currency}",
                        value=float(live_rate),
                        format="%.6f",
                        key=fx_input_key,
                        help=f"Exchange rate: How many {home_currency} per 1 {source_curr}. Auto-fetched from Yahoo Finance. You can override this value if needed."
                    )
                    
                    # Validate FX rate
                    if fx_rate <= 0:
                        st.error(f"❌ Invalid FX rate for source {i+1}. Must be > 0.")
                        fx_rate = 1.0
                    
                    # Show rate verification (helpful for debugging)
                    if abs(fx_rate - live_rate) > 0.0001:
                        st.caption(f"ℹ️ Using manual rate. Auto-fetched was: {live_rate:.6f}")
                    
                    # Convert to home currency
                    home_value = raw_amount * fx_rate
                else:
                    fx_rate = 1.0
                    home_value = raw_amount
                    col3.markdown(f"**1:1**<br><small>(Same currency)</small>", unsafe_allow_html=True)
                
                # Cost/Rate input
                cost_rate = col4.number_input(
                    f"{cost_label} (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=default_cost,
                    step=0.1,
                    key=f"{source_type.lower()}_{i}_cost"
                ) / 100.0
                
                # Display converted value
                if source_curr != home_currency:
                    st.caption(f"💱 Converted Value: **{home_currency} {home_value:,.2f}**")
                
                # Accumulate totals
                total_value += home_value
                total_weighted_cost += (home_value * cost_rate)
                
                # Store details for breakdown
                details.append({
                    'Source': f"{source_type} {i+1}",
                    'Currency': source_curr,
                    'Original Amount': raw_amount,
                    'FX Rate': fx_rate if source_curr != home_currency else '-',
                    f'{home_currency} Value': home_value,
                    f'{cost_label} (%)': cost_rate * 100
                })
                
                st.divider()
    
    # Create details DataFrame
    details_df = pd.DataFrame(details) if details else pd.DataFrame()
    
    return total_value, total_weighted_cost, details_df


# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
    <style>
    .formula-container {
        font-family: 'Courier New', Courier, monospace;
        font-size: 20px;
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        border: 1px solid #dee2e6;
        margin: 20px 0;
    }
    .term { 
        transition: all 0.3s ease; 
        padding: 2px 5px; 
        border-radius: 4px; 
    }
    .term-active { 
        color: #198754; 
        font-weight: bold; 
        background-color: #d1e7dd; 
    }
    .term-inactive { 
        color: #adb5bd; 
    }
    .operator { 
        color: #495057; 
        font-weight: bold; 
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
    .stAlert {
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR / GLOBAL SETTINGS
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Global Settings")
    
    CURRENCY_OPTIONS = [
        "USD", "EUR", "GBP", "JPY", "CAD", 
        "AUD", "CNY", "INR", "CHF", "SEK", 
        "NOK", "DKK", "SGD", "HKD", "NZD"
    ]
    
    home_currency = st.selectbox(
        "🏠 Home (Reporting) Currency",
        CURRENCY_OPTIONS,
        index=0,
        help="All foreign amounts will be converted to this currency",
        key="home_currency_select"
    )
    
    st.divider()
    
    st.subheader("Corporate Tax Settings")
    tax_rate = st.number_input(
        "Tax Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=21.0,
        step=0.1,
        help="Corporate tax rate for calculating tax shield on debt"
    ) / 100.0
    
    st.divider()
    
    st.markdown("### 📚 About WACC")
    st.markdown("""
    **Weighted Average Cost of Capital (WACC)** represents the average rate 
    a company expects to pay to finance its assets.
    
    **Formula:**
    ```
    WACC = (E/V × Re) + (D/V × Rd × (1-T))
    ```
    
    Where:
    - E = Market value of equity
    - D = Market value of debt
    - V = E + D (total firm value)
    - Re = Cost of equity
    - Rd = Cost of debt
    - T = Tax rate
    """)
    
    st.divider()
    
    # Add refresh button for FX rates
    if st.button("🔄 Refresh FX Rates", use_container_width=True):
        st.cache_data.clear()
        st.success("✅ FX rates cache cleared! Rates will refresh on next calculation.")
        st.info("💡 Tip: FX rates auto-refresh every hour.")

# -----------------------------------------------------------------------------
# MAIN APP
# -----------------------------------------------------------------------------
st.title("🌐 Global WACC Calculator")
st.markdown(f"Calculate Weighted Average Cost of Capital reporting in **{home_currency}**.")
st.markdown("---")

# -----------------------------------------------------------------------------
# EQUITY CAPITAL
# -----------------------------------------------------------------------------
st.header("1️⃣ Equity Capital")
equity_value, equity_weighted_cost, equity_details = render_capital_sources(
    source_type="Equity",
    home_currency=home_currency,
    currency_options=CURRENCY_OPTIONS,
    default_num=1,
    default_cost=10.0,
    cost_label="Cost of Equity"
)

# Calculate blended cost of equity
if equity_value > 0:
    cost_of_equity = equity_weighted_cost / equity_value
else:
    cost_of_equity = 0.0

st.info(f"**📊 Total Equity (E):** {home_currency} {equity_value:,.2f}  |  **Cost of Equity (Re):** {cost_of_equity:.2%}")

# -----------------------------------------------------------------------------
# DEBT CAPITAL
# -----------------------------------------------------------------------------
st.header("2️⃣ Debt Capital")
debt_value, debt_weighted_cost, debt_details = render_capital_sources(
    source_type="Debt",
    home_currency=home_currency,
    currency_options=CURRENCY_OPTIONS,
    default_num=1,
    default_cost=5.0,
    cost_label="Interest Rate"
)

# Calculate blended cost of debt
if debt_value > 0:
    cost_of_debt = debt_weighted_cost / debt_value
else:
    cost_of_debt = 0.0

st.info(f"**📊 Total Debt (D):** {home_currency} {debt_value:,.2f}  |  **Cost of Debt (Rd):** {cost_of_debt:.2%}")

# -----------------------------------------------------------------------------
# VALIDATION
# -----------------------------------------------------------------------------
total_firm_value = equity_value + debt_value

if total_firm_value == 0:
    st.warning("⚠️ **Total firm value is zero.** Please enter equity and/or debt capital amounts to calculate WACC.")
    st.stop()

# -----------------------------------------------------------------------------
# WACC CALCULATION
# -----------------------------------------------------------------------------
st.markdown("---")
st.header("3️⃣ WACC Calculation")

# Calculate WACC
equity_weight = equity_value / total_firm_value
debt_weight = debt_value / total_firm_value
tax_shield = 1 - tax_rate

wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * tax_shield)

# Check for anomalies
if wacc < 0:
    st.error("❌ **Negative WACC detected.** Please review your inputs - this is unusual and may indicate an error.")
elif wacc > 1.0:
    st.warning("⚠️ **WACC exceeds 100%.** This is highly unusual - please verify your cost inputs.")

# -----------------------------------------------------------------------------
# DYNAMIC FORMULA VISUALIZATION
# -----------------------------------------------------------------------------
def get_cls(val): 
    return "term-active" if val > 0 else "term-inactive"

html_formula = f"""
<div class="formula-container">
    WACC = 
    [ 
    <span class="term {get_cls(equity_value)}" title="Total Equity: {home_currency} {equity_value:,.2f}">E</span> 
    <span class="operator">/</span> 
    <span class="term {get_cls(total_firm_value)}" title="Total Firm Value: {home_currency} {total_firm_value:,.2f}">V</span> 
    <span class="operator">×</span> 
    <span class="term {get_cls(cost_of_equity)}" title="Cost of Equity: {cost_of_equity:.2%}">Re</span> 
    ]
    <span class="operator">+</span>
    [ 
    <span class="term {get_cls(debt_value)}" title="Total Debt: {home_currency} {debt_value:,.2f}">D</span> 
    <span class="operator">/</span> 
    <span class="term {get_cls(total_firm_value)}" title="Total Firm Value: {home_currency} {total_firm_value:,.2f}">V</span> 
    <span class="operator">×</span> 
    <span class="term {get_cls(cost_of_debt)}" title="Cost of Debt: {cost_of_debt:.2%}">Rd</span> 
    <span class="operator">×</span> 
    (1 - <span class="term {get_cls(tax_rate)}" title="Tax Rate: {tax_rate:.2%}">T</span>) 
    ]
</div>
"""

st.markdown(html_formula, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# FINAL METRICS DASHBOARD
# -----------------------------------------------------------------------------
st.subheader("📈 Results Summary")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Firm Value (V)",
        f"{home_currency} {total_firm_value:,.0f}",
        help="Sum of all equity and debt"
    )

with col2:
    st.metric(
        "Cost of Equity (Re)",
        f"{cost_of_equity:.2%}",
        help="Weighted average cost of all equity sources"
    )

with col3:
    st.metric(
        "Cost of Debt (Rd)",
        f"{cost_of_debt:.2%}",
        help="Weighted average cost of all debt sources"
    )

with col4:
    st.metric(
        "**WACC**",
        f"{wacc:.2%}",
        delta="Calculated",
        delta_color="off",
        help="Weighted Average Cost of Capital"
    )

# Additional metrics row
col5, col6, col7, col8 = st.columns(4)

with col5:
    st.metric(
        "Equity Weight",
        f"{equity_weight:.1%}",
        help="E/V ratio"
    )

with col6:
    st.metric(
        "Debt Weight",
        f"{debt_weight:.1%}",
        help="D/V ratio"
    )

with col7:
    st.metric(
        "After-Tax Cost of Debt",
        f"{cost_of_debt * tax_shield:.2%}",
        help=f"Rd × (1 - T) = {cost_of_debt:.2%} × {tax_shield:.2%}"
    )

with col8:
    st.metric(
        "Tax Shield",
        f"{tax_shield:.1%}",
        help=f"1 - {tax_rate:.1%}"
    )

# -----------------------------------------------------------------------------
# DETAILED BREAKDOWN
# -----------------------------------------------------------------------------
st.markdown("---")

with st.expander("📊 Detailed Capital Structure Breakdown", expanded=False):
    tab1, tab2, tab3 = st.tabs(["Equity Details", "Debt Details", "Combined View"])
    
    with tab1:
        if not equity_details.empty:
            st.dataframe(
                equity_details.style.format({
                    'Original Amount': '{:,.2f}',
                    f'{home_currency} Value': '{:,.2f}',
                    'Cost of Equity (%)': '{:.2f}',
                    'FX Rate': lambda x: '{:.6f}'.format(x) if isinstance(x, (int, float)) else x
                }),
                use_container_width=True
            )
            
            # Summary stats
            st.markdown("**Summary:**")
            st.write(f"- Total Equity Sources: {len(equity_details)}")
            st.write(f"- Total Equity Value: {home_currency} {equity_value:,.2f}")
            st.write(f"- Weighted Average Cost: {cost_of_equity:.2%}")
        else:
            st.info("No equity sources entered.")
    
    with tab2:
        if not debt_details.empty:
            st.dataframe(
                debt_details.style.format({
                    'Original Amount': '{:,.2f}',
                    f'{home_currency} Value': '{:,.2f}',
                    'Interest Rate (%)': '{:.2f}',
                    'FX Rate': lambda x: '{:.6f}'.format(x) if isinstance(x, (int, float)) else x
                }),
                use_container_width=True
            )
            
            # Summary stats
            st.markdown("**Summary:**")
            st.write(f"- Total Debt Sources: {len(debt_details)}")
            st.write(f"- Total Debt Value: {home_currency} {debt_value:,.2f}")
            st.write(f"- Weighted Average Cost: {cost_of_debt:.2%}")
            st.write(f"- After-Tax Cost: {cost_of_debt * tax_shield:.2%}")
        else:
            st.info("No debt sources entered.")
    
    with tab3:
        # Combined capital structure
        combined_data = {
            'Capital Type': ['Equity', 'Debt', 'Total'],
            f'Value ({home_currency})': [equity_value, debt_value, total_firm_value],
            'Weight (%)': [equity_weight * 100, debt_weight * 100, 100.0],
            'Cost (%)': [cost_of_equity * 100, cost_of_debt * 100, '-'],
            'After-Tax Cost (%)': [cost_of_equity * 100, cost_of_debt * tax_shield * 100, wacc * 100]
        }
        
        df_combined = pd.DataFrame(combined_data)
        st.dataframe(
            df_combined.style.format({
                f'Value ({home_currency})': '{:,.2f}',
                'Weight (%)': '{:.2f}',
                'Cost (%)': lambda x: '{:.2f}'.format(x) if x != '-' else x,
                'After-Tax Cost (%)': '{:.2f}'
            }),
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# CALCULATION LOGIC DISCLOSURE
# -----------------------------------------------------------------------------
with st.expander("🔍 View Python Calculation Logic"):
    st.code(f"""
# ============================================================================
# GLOBAL WACC CALCULATOR - CALCULATION LOGIC
# ============================================================================

# 1. FOREIGN EXCHANGE CONVERSION
# --------------------------------
# FX Rate Definition: How many {home_currency} per 1 unit of Foreign Currency
# Example: If 1 EUR = 1.05 USD, then FX_rate = 1.05
#
# Conversion Formula:
#   Foreign Amount × FX Rate = Home Currency Amount
#   Example: 100,000 EUR × 1.05 = 105,000 USD

# 2. CAPITAL AGGREGATION
# ----------------------
Total_Equity = {equity_value:,.2f} {home_currency}
Total_Debt   = {debt_value:,.2f} {home_currency}
Total_Value  = {total_firm_value:,.2f} {home_currency}

# 3. WEIGHTED AVERAGE COSTS
# --------------------------
# For each capital source i:
#   Weighted_Cost_i = Value_i × Cost_i
#
# Blended Cost = Sum(Weighted_Cost_i) / Sum(Value_i)

Cost_of_Equity = {cost_of_equity:.6f}  # {cost_of_equity:.2%}
Cost_of_Debt   = {cost_of_debt:.6f}  # {cost_of_debt:.2%}

# 4. WACC FORMULA
# ---------------
# Standard WACC with tax shield on debt:

Equity_Weight = Total_Equity / Total_Value  # {equity_weight:.6f}
Debt_Weight   = Total_Debt / Total_Value    # {debt_weight:.6f}
Tax_Rate      = {tax_rate:.6f}  # {tax_rate:.2%}
Tax_Shield    = 1 - Tax_Rate    # {tax_shield:.6f}

WACC = (Equity_Weight × Cost_of_Equity) + \\
       (Debt_Weight × Cost_of_Debt × Tax_Shield)

WACC = ({equity_weight:.6f} × {cost_of_equity:.6f}) + \\
       ({debt_weight:.6f} × {cost_of_debt:.6f} × {tax_shield:.6f})

WACC = {wacc:.6f}  # {wacc:.2%}

# ============================================================================
# NOTES:
# ============================================================================
# - Tax shield applies only to debt (interest is tax-deductible)
# - Assumes company is consistently profitable
# - FX rates are live-fetched from Yahoo Finance
# - All foreign amounts are converted using current spot rates
# ============================================================================
    """, language="python")

# -----------------------------------------------------------------------------
# EXPORT FUNCTIONALITY
# -----------------------------------------------------------------------------
st.markdown("---")
st.subheader("📥 Export Results")

# Prepare export data
export_data = {
    'Metric': [
        'Total Equity (E)',
        'Total Debt (D)',
        'Total Firm Value (V)',
        'Cost of Equity (Re)',
        'Cost of Debt (Rd)',
        'Tax Rate (T)',
        'After-Tax Cost of Debt',
        'Equity Weight (E/V)',
        'Debt Weight (D/V)',
        'WACC'
    ],
    'Value': [
        f"{equity_value:,.2f}",
        f"{debt_value:,.2f}",
        f"{total_firm_value:,.2f}",
        f"{cost_of_equity:.4%}",
        f"{cost_of_debt:.4%}",
        f"{tax_rate:.4%}",
        f"{cost_of_debt * tax_shield:.4%}",
        f"{equity_weight:.4%}",
        f"{debt_weight:.4%}",
        f"{wacc:.4%}"
    ],
    'Currency/Unit': [
        home_currency,
        home_currency,
        home_currency,
        'Percentage',
        'Percentage',
        'Percentage',
        'Percentage',
        'Percentage',
        'Percentage',
        'Percentage'
    ]
}

df_export = pd.DataFrame(export_data)

# Download button
csv = df_export.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📄 Download Summary (CSV)",
    data=csv,
    file_name=f"wacc_summary_{home_currency}.csv",
    mime="text/csv",
    use_container_width=True
)

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <small>
        <strong>Global WACC Calculator</strong> | 
        Built with Streamlit & Python | 
        FX rates from Yahoo Finance
        <br>
        ⚠️ For educational purposes only. Consult financial professionals for investment decisions.
    </small>
</div>
""", unsafe_allow_html=True)
