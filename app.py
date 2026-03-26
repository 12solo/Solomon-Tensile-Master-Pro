import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from scipy.interpolate import interp1d
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research Suite - Batch Analysis", layout="wide")

# Initialize Session State for Multi-Sample Storage
if 'samples' not in st.session_state:
    st.session_state.samples = {}

# --- 2. Professional Header & Logo ---
logo_url = "https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png"
col_logo, col_text = st.columns([1, 5])
with col_logo:
    try:
        st.image(logo_url, width=150)
    except:
        st.header("🔬")
with col_text:
    st.title("Solomon Tensile Suite: Research Edition")
    st.markdown("**Advanced Statistical Master Curve & Batch Analytics** 🚀")

# --- 3. Sidebar: Global Metadata & QC ---
st.sidebar.header("📂 Research Metadata")
project_name = st.sidebar.text_input("Project Name", "PBAT/PLA Synergy Study")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)
target_def = st.sidebar.number_input("Target Extrapolation (mm)", value=400.0)

st.sidebar.header("✍️ Validation & QC")
verified_by = st.sidebar.text_input("Digital Signature", "Solomon Dufera Tolcha")
qc_status = st.sidebar.selectbox("QC Approval", ["Pending", "Approved", "Requires Re-test"])

if st.sidebar.button("Clear All Data"):
    st.session_state.samples = {}
    st.rerun()

# --- 4. Data Acquisition ---
st.subheader("1. Populate Batch Dataset")
uploaded_file = st.file_uploader("Upload Sample Data (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    sample_name = st.text_input("Sample Label (e.g., S1-Control)", uploaded_file.name.split('.')[0])
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    c1, c2 = st.columns(2)
    with c1: f_col = st.selectbox("Force Column (N)", cols, key=f"f_{sample_name}")
    with c2: d_col = st.selectbox("Deformation Column (mm)", cols, key=f"d_{sample_name}")
    
    if st.button(f"Add {sample_name} to Research Batch"):
        # Unit Conversion to Stress/Strain
        stress = df_raw[f_col].values / area
        strain = (df_raw[d_col].values / gauge_length) * 100
        
        # High-Fidelity Extrapolation
        slope, _ = np.polyfit(strain[-30:], stress[-30:], 1)
        target_strain = (target_def / gauge_length) * 100
        strain_ext = np.linspace(strain[-1], target_strain, 100)
        stress_ext = stress[-1] + slope * (strain_ext - strain[-1])
        
        full_strain = np.concatenate([strain, strain_ext[1:]])
        full_stress = np.concatenate([stress, stress_ext[1:]])
        
        st.session_state.samples[sample_name] = {"strain": full_strain, "stress": full_stress}
        st.success(f"Sample '{sample_name}' integrated successfully.")

# --- 5. Statistical Analytics Engine ---
if st.session_state.samples:
    st.divider()
    st.subheader("2. Statistical Master Curve & Comparison")
    
    # Interpolation for Statistical Consistency
    max_grid_strain = (target_def / gauge_length) * 100
    common_strain = np.linspace(0, max_grid_strain, 500)
    all_stresses = []
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot Individual Traces
    for name, data in st.session_state.samples.items():
        f_interp = interp1d(data['strain'], data['stress'], bounds_error=False, fill_value="extrapolate")
        interp_stress = f_interp(common_strain)
        all_stresses.append(interp_stress)
        ax.plot(common_strain, interp_stress, color='grey', alpha=0.25, lw=1)

    # Calculate Mean & Standard Deviation
    master_mean = np.mean(all_stresses, axis=0)
    master_std = np.std(all_stresses, axis=0)
    
    # Plot Master Curve with Confidence Interval
    ax.plot(common_strain, master_mean, color='#1f77b4', label='MASTER CURVE (Mean)', lw=3)
    ax.fill_between(common_strain, master_mean - master_std, master_mean + master_std, color='#1f77b4', alpha=0.15, label='Standard Deviation')
    
    ax.set_xlabel("Strain (%)", fontweight='bold')
    ax.set_ylabel("Stress (MPa)", fontweight='bold')
    ax.set_title(f"Project: {project_name} | Comparative Mechanical Analysis", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.2)
    st.pyplot(fig)
    
    # --- 6. Export Branded Research Report ---
    st.subheader("3. Export Formal Documentation")
    
    # Summary Table for Excel
    df_master = pd.DataFrame({
        'Strain (%)': common_strain,
        'Mean Stress (MPa)': master_mean,
        'Std Dev (MPa)': master_
