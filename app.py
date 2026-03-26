import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from scipy import stats
from statsmodels.stats.power import TTestIndPower
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research - Power & Significance", layout="wide")

# Initialize Session State Groups
if 'group_a' not in st.session_state: st.session_state.group_a = {}
if 'group_b' not in st.session_state: st.session_state.group_b = {}

# --- 2. Professional Header & Logo ---
logo_url = "https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png"
col_logo, col_text = st.columns([1, 5])
with col_logo:
    try: st.image(logo_url, width=150)
    except: st.header("🔬")
with col_text:
    st.title("Solomon Tensile Suite: Research Edition v2.3")
    st.markdown("**Advanced Statistical Power ($1-β$) & Hypothesis Testing ($p < 0.05$)** 🚀")

# --- 3. Sidebar: Research Metadata ---
st.sidebar.header("📂 Global Parameters")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("🧪 Group Comparison Labels")
name_a = st.sidebar.text_input("Group A (Control)", "PBAT-Pure")
name_b = st.sidebar.text_input("Group B (Experimental)", "PBAT-PLA-Blend")

st.sidebar.header("📏 Modulus Bounds (%)")
ym_start = st.sidebar.slider("Start", 0.0, 1.0, 0.2)
ym_end = st.sidebar.slider("End", 0.5, 5.0, 1.0)

if st.sidebar.button("🗑️ Reset All Data"):
    st.session_state.group_a = {}; st.session_state.group_b = {}
    st.rerun()

# --- 4. Data Acquisition Section ---
st.subheader("1. Load Batch Data into Research Groups")
uploaded_file = st.file_uploader("Upload Tensile Test File (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    target_group = st.radio("Assign Sample to:", [name_a, name_b], horizontal=True)
    sample_label = st.text_input("Unique Sample ID", uploaded_file.name.split('.')[0])
    
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    c1, c2 = st.columns(2)
    with c1: f_col = st.selectbox("Force (N)", cols, index=0)
    with c2: d_col = st.selectbox("Deformation (mm)", cols, index=1 if len(cols)>1 else 0)

    if st.button(f"Integrate into {target_group}"):
        # Core Physics
        stress = df_raw[f_col].values / area
        strain = (df_raw[d_col].values / gauge_length) * 100
        
        # Metric Extraction
        mask = (strain >= ym_start) & (strain <= ym_end)
        E, _ = np.polyfit(strain[mask]/100, stress[mask], 1)
        y_stress = stress[strain <= 25.0].max() # Yield search limit 25%
        
        metrics = {
            "E (MPa)": E,
            "Yield (MPa)": y_stress,
            "Break (MPa)": stress[-1],
            "Elongation (%)": strain[-1],
            "Work (J)": np.trapz(df_raw[f_col], df_raw[d_col]) / 1000.0,
            "Raw_Strain": strain,
            "Raw_Stress": stress
        }
        
        if target_group == name_a: st.session_state.group_a[sample_label] = metrics
        else: st.session_state.group_b[sample_label] = metrics
        st.success(f"Sample {sample_label} successfully assigned to {target_group}.")

# --- 5. T-Test & Power Analysis Engine ---
if st.session_state.group_a and st.session_state.group_b:
    st.divider()
    st.subheader("2. Statistical Significance & Power Analysis")

    # Prepare DataFrames (filtering out raw arrays for table)
    df_a = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.group_a.items()}).T
    df_b = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.group_b.items()}).T
    
    comp_data = []
    power_gen = TTestIndPower()

    for col in df_a.columns:
        # T-Test (Welch's)
        t_stat, p_val = stats.ttest_ind(df_a[col], df_b[col], equal_var=False)
        
        # Cohen's d Effect Size
        n1, n2 = len(df_a), len(df_b)
        s1, s2 = df_a[col].std(), df_b[col].std()
        pooled_std = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
        d = abs(df_a[col].mean() - df_b[col].mean()) / pooled_std
        
        # Power Analysis
        obs_power = power_gen.solve_power(effect_size=d, nobs1=n1, ratio=n2/n1, alpha=0.05)
        req_n = power_gen.solve_power(effect_size=d, power=0.80, alpha=0.05)
        
        comp_data.append({
            "Property": col,
            f"Mean {name_a}": df_a[col].mean(),
            f"Mean {name_b}": df_b[col].mean(),
            "p-value": p_val,
            "Effect Size (d)": d,
            "Power (1-β)": obs_power,
            "Verdict": "✅ Significant" if p_val < 0.05 else "❌ Not Sig.",
            "Req. N (80% Power)": int(np.ceil(req_n)) if not np.isinf(req_n) else "N/A"
        })

    # Display Table
    summary_df = pd.DataFrame(comp_data)
    st.dataframe(summary_df.style.format(precision=3).applymap(
        lambda x: 'background-color: #d4edda' if x == "✅ Significant" else '', subset=['Verdict']
    ), use_container_width=True)

    # Visualization: Visual Variance Comparison
    st.subheader("3. Comparative Visualizations")
    col_plot1, col_plot2 = st.columns(2)
    
    with col_plot1:
        # Stress-Strain Overlay
        fig1, ax1 = plt.subplots()
        for _, d in st.session_state.group_a.items(): ax1.plot(d['Raw_Strain'], d['Raw_Stress'], color='blue', alpha=0.3)
        for _, d in st.session_state.group_b.items(): ax1.plot(d['Raw_Strain'], d['Raw_Stress'], color='red', alpha=0.3)
        ax1.set_title("Overlay: Group A (Blue) vs Group B (Red)"); ax1.set_xlabel("Strain (%)"); ax1.set_ylabel("Stress (MPa)")
        st.pyplot(fig1)

    with col_plot2:
        # Boxplot for Modulus
        fig2, ax2 = plt.subplots()
        ax2.boxplot([df_a["E (MPa)"], df_b["E (MPa)"]], labels=[name_a, name_b])
        ax2.set_title("Variance Comparison: Young's Modulus (E)"); ax2.set_ylabel("MPa")
        st.pyplot(fig2)

    # --- 6. Export Final Research Document ---
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        summary_df.to_excel(writer, sheet_name="Statistical Analysis", index=False)
        df_a.to_excel(writer, sheet_name=f"Data_{name_a[:10]}")
        df_b.to_excel(writer, sheet_name=f"Data_{name_b[:10]}")
        
    st.download_button("📥 Download Final Research Report", output.getvalue(), f"Research_Significance_{datetime.now().strftime('%Y%m%d')}.xlsx")

else:
    st.warning(f"Please add at least one sample to BOTH '{name_a}' and '{name_b}' to generate statistical analytics.")
