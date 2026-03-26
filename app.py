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
st.set_page_config(page_title="Solomon Research - Bulk Analytics", layout="wide")

if 'group_a' not in st.session_state: st.session_state.group_a = {}
if 'group_b' not in st.session_state: st.session_state.group_b = {}

# --- 2. Header ---
st.title("Solomon Tensile Suite: Research Edition v2.4")
st.markdown("**Bulk Data Processing & Automatic Slack Normalization (Zeroing)** 🚀")

# --- 3. Sidebar: Global Parameters ---
st.sidebar.header("📂 Global Parameters")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("🧪 Group Labels")
name_a = st.sidebar.text_input("Group A", "Control")
name_b = st.sidebar.text_input("Group B", "Experimental")

st.sidebar.header("⚙️ Processing Options")
normalize = st.sidebar.checkbox("Normalize (Shift to 0,0)", value=True, help="Removes initial slack by shifting the first load point to the origin.")
ym_start = st.sidebar.slider("Modulus Start (%)", 0.0, 1.0, 0.2)
ym_end = st.sidebar.slider("Modulus End (%)", 0.5, 5.0, 1.0)

if st.sidebar.button("🗑️ Clear All Data"):
    st.session_state.group_a = {}; st.session_state.group_b = {}
    st.rerun()

# --- 4. Bulk Data Acquisition ---
st.subheader("1. Bulk Upload & Group Assignment")
# accept_multiple_files=True is the key change here
uploaded_files = st.file_uploader("Upload Multiple Files (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    target_group = st.radio("Assign these files to:", [name_a, name_b], horizontal=True)
    
    if st.button(f"Process and Integrate {len(uploaded_files)} Files"):
        for uploaded_file in uploaded_files:
            sample_label = uploaded_file.name.split('.')[0]
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # Identify columns (assuming Force is Col 0 and Def is Col 1)
            f_raw = df_raw.iloc[:, 0].values
            d_raw = df_raw.iloc[:, 1].values

            # --- NORMALIZATION LOGIC ---
            if normalize:
                # Find the first index where force exceeds a small threshold (0.05N)
                start_idx = np.where(f_raw > 0.05)[0][0] if any(f_raw > 0.05) else 0
                f_proc = f_raw[start_idx:] - f_raw[start_idx]
                d_proc = d_raw[start_idx:] - d_raw[start_idx]
            else:
                f_proc, d_proc = f_raw, d_raw

            stress = f_proc / area
            strain = (d_proc / gauge_length) * 100
            
            # Metric Extraction
            mask = (strain >= ym_start) & (strain <= ym_end)
            if len(strain[mask]) > 1:
                E, _ = np.polyfit(strain[mask]/100, stress[mask], 1)
            else:
                E = 0
            
            y_stress = stress[strain <= 25.0].max()
            
            try:
                work_j = np.trapezoid(f_proc, d_proc) / 1000.0
            except:
                work_j = np.trapz(f_proc, d_proc) / 1000.0
            
            metrics = {
                "E (MPa)": E, "Yield (MPa)": y_stress, "Break (MPa)": stress[-1],
                "Elongation (%)": strain[-1], "Work (J)": work_j,
                "Raw_Strain": strain, "Raw_Stress": stress
            }
            
            if target_group == name_a: st.session_state.group_a[sample_label] = metrics
            else: st.session_state.group_b[sample_label] = metrics
            
        st.success(f"Successfully processed {len(uploaded_files)} samples into {target_group}!")

# --- 5. T-Test & Power Analysis Engine ---
if st.session_state.group_a and st.session_state.group_b:
    st.divider()
    st.subheader("2. Statistical Significance & Power Analysis")

    df_a = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.group_a.items()}).T
    df_b = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.group_b.items()}).T
    
    comp_data = []
    power_gen = TTestIndPower()

    for col in df_a.columns:
        t_stat, p_val = stats.ttest_ind(df_a[col], df_b[col], equal_var=False)
        n1, n2 = len(df_a), len(df_b)
        s1, s2 = df_a[col].std(), df_b[col].std()
        pooled_std = np.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2) / (n1+n2-2))
        d = abs(df_a[col].mean() - df_b[col].mean()) / pooled_std
        obs_power = power_gen.solve_power(effect_size=d, nobs1=n1, ratio=n2/n1, alpha=0.05)
        
        comp_data.append({
            "Property": col, f"Mean {name_a}": df_a[col].mean(), f"Mean {name_b}": df_b[col].mean(),
            "p-value": p_val, "Power": obs_power, "Verdict": "✅ Sig" if p_val < 0.05 else "❌ NS"
        })

    st.dataframe(pd.DataFrame(comp_data).style.format(precision=3), use_container_width=True)

    # --- 6. Visualization ---
    fig, ax = plt.subplots(figsize=(10, 5))
    for _, d in st.session_state.group_a.items(): ax.plot(d['Raw_Strain'], d['Raw_Stress'], color='blue', alpha=0.3)
    for _, d in st.session_state.group_b.items(): ax.plot(d['Raw_Strain'], d['Raw_Stress'], color='red', alpha=0.3)
    ax.set_title("Normalized Group Overlay (A=Blue, B=Red)"); ax.set_xlabel("Strain (%)"); ax.set_ylabel("Stress (MPa)")
    st.pyplot(fig)

    # Export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        pd.DataFrame(comp_data).to_excel(writer, sheet_name="Significance", index=False)
        df_a.to_excel(writer, sheet_name="Group_A_Metrics")
        df_b.to_excel(writer, sheet_name="Group_B_Metrics")
    st.download_button("📥 Download Research Report", output.getvalue(), "Bulk_Research_Report.xlsx")
