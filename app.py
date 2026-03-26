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

# --- 4. Bulk Data Acquisition & High-Precision Processing ---
st.subheader("1. Bulk Upload & High-Precision Processing")
uploaded_files = st.file_uploader("Upload Samples (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    # Get group names from sidebar
    g_a_name = st.sidebar.text_input("Group A Label", "Control", key="ga_input")
    g_b_name = st.sidebar.text_input("Group B Label", "Experimental", key="gb_input")
    
    target_group = st.radio("Assign these files to:", [g_a_name, g_b_name], horizontal=True)
    
    if st.button(f"Process {len(uploaded_files)} Samples"):
        for uploaded_file in uploaded_files:
            sample_label = uploaded_file.name.split('.')[0]
            
            # Load Data
            try:
                df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                f_raw = df_raw.iloc[:, 0].values # Force (N)
                d_raw = df_raw.iloc[:, 1].values # Deformation (mm)
            except Exception as e:
                st.error(f"Error reading {uploaded_file.name}: {e}")
                continue

            # 1. Toe-Region / Slack Normalization (Zeroing)
            if normalize:
                # Find first point where force > 0.1N to ignore grip slack
                start_mask = f_raw > 0.1
                if any(start_mask):
                    idx = np.where(start_mask)[0][0]
                    f_proc = f_raw[idx:] - f_raw[idx]
                    d_proc = d_raw[idx:] - d_raw[idx]
                else:
                    f_proc, d_proc = f_raw, d_raw
            else:
                f_proc, d_proc = f_raw, d_raw

            # 2. Stress-Strain Conversion
            stress = f_proc / area
            strain = (d_proc / gauge_length) * 100 # Strain in %

            # 3. ROLLING REGRESSION MODULUS (E)
            # Scans for the maximum slope in the initial region (0% to search_limit%)
            mask_e = (strain > 0) & (strain <= search_limit)
            stress_e = stress[mask_e]
            strain_e = strain[mask_e] / 100 # Convert % back to mm/mm for MPa
            
            E_final = 0
            if len(stress_e) > 10:
                # Use a sliding window of 20% of the elastic data to find the truest slope
                window = max(5, int(len(stress_e) * 0.2))
                slopes = []
                for i in range(len(stress_e) - window):
                    slope, _, _, _, _ = stats.linregress(strain_e[i:i+window], stress_e[i:i+window])
                    slopes.append(slope)
                E_final = max(slopes) if slopes else 0

            # 4. YIELD & WORK DONE
            y_stress = stress[strain <= 25.0].max() if any(strain <= 25.0) else stress.max()
            try:
                work_j = np.trapezoid(f_proc, d_proc) / 1000.0
            except:
                work_j = np.trapz(f_proc, d_proc) / 1000.0

            # 5. Store Metrics in Session State
            metrics = {
                "E (MPa)": round(E_final, 2),
                "Yield (MPa)": round(y_stress, 2),
                "Break (MPa)": round(stress[-1], 2),
                "Elongation (%)": round(strain[-1], 2),
                "Work (J)": round(work_j, 4),
                "Raw_Strain": strain,
                "Raw_Stress": stress
            }

            if target_group == g_a_name:
                st.session_state.group_a[sample_label] = metrics
            else:
                st.session_state.group_b[sample_label] = metrics
            
        st.success(f"Processed {len(uploaded_files)} samples successfully!")

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
