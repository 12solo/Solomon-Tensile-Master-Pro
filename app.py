import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import re

# --- 1. Page Config ---
st.set_page_config(page_title="Solomon Tensile Suite Pro", layout="wide")
st.title("Solomon Tensile Suite v2.9")
st.caption("Professional Batch Analysis | Toe-Compensation | Manual Scaling")

# --- 2. Sidebar ---
st.sidebar.header("📏 Specimen Geometry")
thickness = st.sidebar.number_input("Thickness (mm)", value=2.0)
width = st.sidebar.number_input("Width (mm)", value=6.0)
gauge_length = st.sidebar.number_input("Gauge Length (mm)", value=25.0)
area = width * thickness 

st.sidebar.header("⚙️ Unit & Analysis Settings")
# Manual Scale Factor: 1.0 (Normal), 0.001 (mm to m), 1000 (mm to um)
manual_scale = st.sidebar.number_input("Displacement Scale Factor", value=1.0, help="Multiply raw displacement by this value.")
apply_zeroing = st.sidebar.checkbox("Apply Toe-Compensation", value=True)
ym_start = st.sidebar.slider("Modulus Start Strain (%)", 0.0, 5.0, 0.2)
ym_end = st.sidebar.slider("Modulus End Strain (%)", 0.1, 20.0, 1.0)

# --- 3. Robust Data Loader ---
def smart_load(file):
    try:
        raw_bytes = file.getvalue()
        content = raw_bytes.decode("utf-8", errors="ignore")
        lines = content.splitlines()
        
        start_row = 0
        for i, line in enumerate(lines):
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", line)
            if len(nums) >= 2:
                start_row = i
                break
        
        sep = '\t' if '\t' in lines[start_row] else (',' if ',' in lines[start_row] else r'\s+')
        df = pd.read_csv(io.StringIO("\n".join(lines[start_row:])), sep=sep, engine='python', on_bad_lines='skip')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except: return None

# --- 4. Main Engine ---
uploaded_files = st.file_uploader("Upload Samples", type=['csv', 'xlsx', 'txt'], accept_multiple_files=True)

if uploaded_files:
    all_results = []
    fig = go.Figure()

    for file in uploaded_files:
        df = smart_load(file)
        if df is None or df.empty: continue
        
        cols = df.columns.tolist()
        f_col = next((c for c in cols if any(k in c.lower() for k in ['load', 'force', 'n'])), cols[0])
        d_col = next((c for c in cols if any(k in c.lower() for k in ['ext', 'disp', 'mm', 'dist', 'pos'])), cols[1])
        
        df[f_col] = pd.to_numeric(df[f_col], errors='coerce')
        df[d_col] = pd.to_numeric(df[d_col], errors='coerce')
        df = df.dropna(subset=[f_col, d_col])

        # Apply Manual Scaling and calculate raw Stress/Strain
        disp_mm = df[d_col].values * manual_scale
        raw_stress = df[f_col].values / area
        raw_strain = (disp_mm / gauge_length) * 100
        
        # Check for empty data in modulus range
        mask_e = (raw_strain >= ym_start) & (raw_strain <= ym_end)
        if np.sum(mask_e) < 3:
            st.error(f"❌ {file.name}: Range mismatch. Max Strain: {raw_strain.max():.1f}%. Adjust Sliders or Scale Factor.")
            continue

        # --- Modulus & Toe-Compensation ---
        E_slope, intercept_y = np.polyfit(raw_strain[mask_e], raw_stress[mask_e], 1)
        
        if apply_zeroing:
            shift = -intercept_y / E_slope
            strain = raw_strain - shift
            # Filter for positive strain
            mask_pos = strain >= 0
            strain, stress = strain[mask_pos], raw_stress[mask
