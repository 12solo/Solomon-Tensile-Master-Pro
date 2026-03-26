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
st.title("Solomon Tensile Suite: Research Edition v2.5.1")
st.markdown("**High-Precision Bulk Processing & Statistical Validation** 🚀")

# --- 3. Sidebar: Global Parameters ---
st.sidebar.header("📂 Global Parameters")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("🧪 Group Labels")
g_a_name = st.sidebar.text_input("Group A Label", "Control")
g_b_name = st.sidebar.text_input("Group B Label", "Experimental")

st.sidebar.header("⚙️ Precision Settings")
normalize = st.sidebar.checkbox("Toe-Region Correction", value=True)
search_limit = st.sidebar.slider("Modulus Search Limit (Strain %)", 0.5, 5.0, 2.0)

if st.sidebar.button("🗑️ Clear All Data"):
    st.session_state.group_a = {}; st.session_state.group_b = {}
    st.rerun()

# --- 4. Bulk Data Acquisition ---
st.subheader("1. Bulk Upload & High-Precision Processing")
uploaded_files = st.file_uploader("Upload Samples (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    target_group = st.radio("Assign these files to:", [g_a_name, g_b_name], horizontal=True)
    
    if st.button(f"Process {len(uploaded_files)} Samples"):
        for uploaded_file in uploaded_files:
            sample_label = uploaded_file.name.split('.')[0]
            
            # Load Data
            try:
                df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                f_raw = df_raw.iloc[:, 0].values 
                d_raw = df_raw.iloc[:, 1].values 
            except Exception as e:
                st.error(f"Error reading {uploaded_file.name}: {e}")
                continue

            # 1. Normalization
            if normalize:
                start_mask = f_raw > 0.1
                idx = np.where(start_mask)[0][0] if any(start_mask) else 0
                f_p, d_p = f_raw[idx:] - f_raw[idx], d_raw[idx:] - d_raw[idx]
            else:
                f_p, d_p = f_raw, d_raw

            stress = f_p / area
            strain = (d_p / gauge_length) * 100 

            # 2. Rolling Modulus (The Math Fix)
            mask_e = (strain > 0) & (strain <= search_limit)
            stress_e = stress[mask_e]
            strain_e = strain[mask_e] / 100 # mm/mm
            
            E_final = 0
            if len(stress_e) > 10:
                window = max(5, int(len(stress_e) * 0.2))
                slopes = []
                for i in range(len(stress_e) - window):
                    slope, _, _, _, _ = stats.linregress(strain_e[i:i+window], stress_e[i:i+window])
                    slopes.append(slope)
                E_final = max(slopes) if slopes else 0

            # 3. Yield & Energy (The NumPy 2.0 Fix)
            y_stress = stress[strain <= 25.0].max() if any(strain <= 25.0) else stress.max()
            try:
                work_j = np.trapezoid(f_p, d_p) / 1000.0
            except AttributeError:
                work_j = np.trapz(f_p, d_p) / 1000.0

            metrics = {
                "E (MPa)": round(E_final, 2), "Yield (MPa)": round(y_stress, 2),
                "Break (MPa)": round(stress[-1], 2), "Elongation (%)": round(strain[-1], 2),
                "Work (J)": round(work_j, 4), "Raw_Strain": strain, "Raw_Stress": stress
            }

            if target_group == g_a_name:
                st.session_state.group_a[sample_label] = metrics
            else:
                st.session_state.group_b[sample_label] = metrics
            
        st.success(f"Processed {len(uploaded_files)} samples successfully!")

# --- 5. Statistics & Visualization ---
if st.session_state.group_a and st.session_state.group_b:
    st.divider()
    df_a = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.group_a.items()}).T
    df_b = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.group_b.items()}).T
    
    # Statistical T-Test
    comp_data = []
    for col in df_a.columns:
        _, p_val = stats.ttest_ind(df_a[col], df_b[col], equal_var=False)
        comp_data.append({"Property": col, f"{g_a_name} Mean": df_a[col].mean(), f"{g_b_name} Mean": df_b[col].mean(), "p-value": p_val})
    
    st.subheader("2. Statistical Significance")
    st.dataframe(pd.DataFrame(comp_data).style.format(precision=3))

    # Visualization
    fig, ax = plt.subplots(figsize=(10, 5))
    for _, d in st.session_state.group_a.items(): ax.plot(d['Raw_Strain'], d['Raw_Stress'], color='blue', alpha=0.3)
    for _, d in st.session_state.group_b.items(): ax.plot(d['Raw_Strain'], d['Raw_Stress'], color='red', alpha=0.3)
    ax.set_xlabel("Strain (%)"); ax.set_ylabel("Stress (MPa)"); ax.set_title("Group Overlay")
    st.pyplot(fig)
