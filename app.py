import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy import stats
from statsmodels.stats.power import TTestIndPower
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research - High Precision", layout="wide")

if 'group_a' not in st.session_state: st.session_state.group_a = {}
if 'group_b' not in st.session_state: st.session_state.group_b = {}

# --- 2. Header ---
st.title("Solomon Tensile Suite: Research Edition v2.5")
st.markdown("**High-Precision Constitutive Modeling & Statistical Validation** 🚀")

# --- 3. Sidebar: Global Parameters ---
st.sidebar.header("📂 Global Parameters")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("⚙️ Precision Settings")
normalize = st.sidebar.checkbox("Toe-Region Correction", value=True, help="Removes initial slack (toe) before calculation.")
# User defines where the search for Modulus happens
search_limit = st.sidebar.slider("Modulus Search Limit (Strain %)", 0.5, 5.0, 2.0)

if st.sidebar.button("🗑️ Clear All Data"):
    st.session_state.group_a = {}; st.session_state.group_b = {}
    st.rerun()

# --- 4. Bulk Data Acquisition ---
st.subheader("1. Bulk Upload & High-Precision Processing")
uploaded_files = st.file_uploader("Upload Samples (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    target_group = st.radio("Assign these files to:", [st.sidebar.text_input("Group A Label", "Control"), st.sidebar.text_input("Group B Label", "Experimental")], horizontal=True)
    
    if st.button(f"Process {len(uploaded_files)} Samples"):
        for uploaded_file in uploaded_files:
            sample_label = uploaded_file.name.split('.')[0]
            df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # 1. Raw Data Extraction
            f_raw = df_raw.iloc[:, 0].values # Force (N)
            d_raw = df_raw.iloc[:, 1].values # Deformation (mm)

            # 2. Toe-Region / Slack Normalization
            # Find point where load significantly starts (0.1N threshold)
            if normalize:
                start_idx = np.where(f_raw > 0.1)[0][0] if any(f_raw > 0.1) else 0
                f_proc = f_raw[start_idx:] - f_raw[start_idx]
                d_proc = d_raw[start_idx:] - d_raw[start_idx]
            else:
                f_proc, d_proc = f_raw, d_raw

            stress = f_proc / area
            strain = (d_proc / gauge_length) * 100 # In %
            
            # 3. HIGH PRECISION MODULUS (E)
            # We search for the maximum slope (stiffness) within the elastic boundary
            mask_elastic = strain <= search_limit
            stress_e = stress[mask_elastic]
            strain_e = strain[mask_elastic] / 100 # mm/mm for MPa unit
            
            if len(stress_e) > 5:
                # Rolling regression to find the most linear 20% of the elastic region
                window = max(5, int(len(stress_e) * 0.2))
                slopes = []
                for i in range(len(stress_e) - window):
                    s, _, _, _, _ = stats.linregress(strain_e[i:i+window], stress_e[i:i+window])
                    slopes.append(s)
                E = max(slopes) if slopes else 0
            else:
                E = 0
            
            # 4. YIELD STRESS (Peak Stress)
            # For PBAT, Yield is often the maximum stress reached in the first 25% strain
            y_stress = stress[strain <= 25.0].max()
            
            # 5. WORK DONE (Numerical Integration)
            try: work_j = np.trapezoid(f_proc, d_proc) / 1000.0
            except: work_j = np.trapz(f_proc, d_proc) / 1000.0
            
            metrics = {
                "E (MPa)": round(E, 2), 
                "Yield (MPa)": round(y_stress, 2), 
                "Elongation (%)": round(strain[-1], 2), 
                "Work (J)": round(work_j, 4),
                "Raw_Strain": strain, "Raw_Stress": stress
            }
            
            if "Control" in target_group: st.session_state.group_a[sample_label] = metrics
            else: st.session_state.
