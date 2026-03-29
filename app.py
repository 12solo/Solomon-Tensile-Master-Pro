import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import re

# --- 1. Page Config ---
st.set_page_config(page_title="Solomon Tensile Suite Pro", layout="wide")
st.title("Solomon Tensile Suite v3.4")
st.info("Manual Unit Override & Scientific Validation Mode")

# --- 2. Sidebar: Professional Inputs ---
st.sidebar.header("📝 Project Metadata")
project_name = st.sidebar.text_input("Research Topic", "PBAT-PLA-Biocomposites")

st.sidebar.header("📏 Specimen Geometry")
thickness = st.sidebar.number_input("Thickness (mm)", value=2.0, step=0.1)
width = st.sidebar.number_input("Width (mm)", value=6.0, step=0.1)
gauge_length = st.sidebar.number_input("Initial Gauge Length (L0) [mm]", value=25.0, step=1.0)
area = width * thickness 

st.sidebar.header("⚙️ Data Calibration")
# Critical for your 1120% error:
unit_input = st.sidebar.selectbox("Raw Displacement Unit", ["Millimeters (mm)", "Micrometers (um)", "Meters (m)"])
scale_map = {"Millimeters (mm)": 1.0, "Micrometers (um)": 0.001, "Meters (m)": 1000.0}
u_scale = scale_map[unit_input]

apply_zeroing = st.sidebar.checkbox("Apply Toe-Compensation (Shift to 0,0)", value=True)
ym_range = st.sidebar.slider("Modulus Fit Range (%)", 0.0, 5.0, (0.2, 1.0))

# --- 3. Robust Data Loader ---
def smart_load(file):
    try:
        raw_bytes = file.getvalue()
        content = raw_bytes.decode("utf-8", errors="ignore")
        lines = content.splitlines()
        # Find first line with at least 2 numbers
        start_row = 0
        for i, line in enumerate(lines):
            if len(re.findall(r"[-+]?\d*\.\d+|\d+", line)) >= 2:
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
        
        # Manual Column Assignment (fallback to first two if keywords fail)
        cols = df.columns.tolist()
        f_col = st.sidebar.selectbox(f"Force Col ({file.name})", cols, index=0, key=f"f_{file.name}")
        d_col = st.sidebar.selectbox(f"Disp Col ({file.name})", cols, index=1, key=f"d_{file.name}")
        
        df[f_col] = pd.to_numeric(df[f_col], errors='coerce')
        df[d_col] = pd.to_numeric(df[d_col], errors='coerce')
        df = df.dropna(subset=[f_col, d_col])

        # 1. Engineering Conversion
        disp_mm = df[d_col].values * u_scale
        stress_raw = df[f_col].values / area
        strain_raw = (disp_mm / gauge_length) * 100
        
        # 2. Modulus Calculation (Slope of elastic region)
        mask_e = (strain_raw >= ym_range[0]) & (strain_raw <= ym_range[1])
        if np.sum(mask_e) < 3:
            st.warning(f"⚠️ {file.name}: Incomplete data in {ym_range}% range. Check units.")
            continue
            
        E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
        
        # 3. Toe-Compensation (Shift X-axis)
        if apply_zeroing:
            shift = -intercept_y / E_slope
            strain = strain_raw - shift
            mask_pos = strain >= 0
            strain, stress = strain[mask_pos], stress_raw[mask_pos]
            f_final, d_final = df[f_col].values[mask_pos], disp_mm[mask_pos]
        else:
            strain, stress = strain_raw, stress_raw
            f_final, d_final = df[f_col].values, disp_mm

        # 4. 0.2% Offset Yield (Standard for Polymers)
        offset_line = E_slope * (strain - 0.2)
        idx_yield = np.where((stress - offset_line) < 0)[0]
        y_stress = stress[idx_yield[0]] if len(idx_yield) > 0 else np.nan
        y_strain = strain[idx_yield[0]] if len(idx_yield) > 0 else np.nan

        # 5. Energy (Work Done) & Toughness
        try: work_j = np.trapezoid(f_final, d_final / 1000.0)
        except: work_j = np.trapz(f_final, d_final / 1000.0)
        
        # Toughness in MJ/m3 (Energy / Volume)
        toughness = (work_j / ((area * gauge_length) * 1e-9)) / 1e6

        all_results.append({
            "Sample": file.name,
            "Modulus (E) [MPa]": round(E_slope * 100, 1),
            "Yield Stress [MPa]": round(y_stress, 2),
            "Yield Strain [%]": round(y_strain, 2),
            "Stress @ Break [MPa]": round(stress[-1], 2),
            "Strain @ Break [%]": round(strain[-1], 2),
            "Work Done [J]": round(work_j, 4),
            "Toughness [MJ/m³]": round(toughness, 3)
        })

        fig.add_trace(go.Scatter(x=strain, y=stress, name=file.name))

    # --- 5. Reporting Dashboard ---
    # ADDED AXIS NAMES HERE
    fig.update_layout(
        xaxis_title="Strain (%)",
        yaxis_title="Stress (MPa)",
        template="plotly_white",
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    if all_results:
        res_df = pd.DataFrame(all_results)
        st.subheader("📊 Batch Summary Statistics")
        st.table(res_df.drop(columns='Sample').agg(['mean', 'std']).T.style.format("{:.2f}"))
        st.dataframe(res_df, hide_index=True)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Summary', index=False)
        st.download_button("📥 Download Official Report", output.getvalue(), f"{project_name}_Final_Report.xlsx")
