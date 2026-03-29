import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import re

# --- 1. Page Config ---
st.set_page_config(page_title="Solomon Tensile Suite Pro", layout="wide")
st.title("Solomon Tensile Suite v3.5")
st.caption("Advanced Data Diagnostics & Multi-Sheet Excel Reporting")

# --- 2. Sidebar: Calibration ---
st.sidebar.header("📝 Project Metadata")
project_name = st.sidebar.text_input("Project Name", "PBAT-PLA-Composite-Analysis")

st.sidebar.header("📏 Specimen Geometry")
thickness = st.sidebar.number_input("Thickness (mm)", value=2.0)
width = st.sidebar.number_input("Width (mm)", value=6.0)
gauge_length = st.sidebar.number_input("Gauge Length (L0) [mm]", value=25.0)
area = width * thickness 

st.sidebar.header("⚙️ Unit Calibration")
unit_input = st.sidebar.selectbox("Raw Displacement Unit", ["mm", "um", "m"])
scale_map = {"mm": 1.0, "um": 0.001, "m": 1000.0}
u_scale = scale_map[unit_input]

apply_zeroing = st.sidebar.checkbox("Apply Toe-Compensation", value=True)
ym_range = st.sidebar.slider("Modulus Range (%)", 0.0, 5.0, (0.2, 1.0))

# --- 3. Robust Data Loader ---
def smart_load(file):
    try:
        raw_bytes = file.getvalue()
        content = raw_bytes.decode("utf-8", errors="ignore")
        lines = content.splitlines()
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
        
        # --- DIAGNOSTICS: Show Raw Column Names ---
        with st.expander(f"🔍 Raw Data Info: {file.name}"):
            st.write(f"**Detected Columns:** `{list(df.columns)}`")
            st.write(df.head(3))
        
        cols = df.columns.tolist()
        f_col = next((c for c in cols if any(k in c.lower() for k in ['load', 'force', 'n'])), cols[0])
        d_col = next((c for c in cols if any(k in c.lower() for k in ['ext', 'disp', 'mm', 'dist', 'pos'])), cols[1])
        
        df[f_col] = pd.to_numeric(df[f_col], errors='coerce')
        df[d_col] = pd.to_numeric(df[d_col], errors='coerce')
        df = df.dropna(subset=[f_col, d_col])

        # Engineering Calculations
        disp_mm = df[d_col].values * u_scale
        stress_raw = df[f_col].values / area
        strain_raw = (disp_mm / gauge_length) * 100
        
        # Modulus & Zeroing
        mask_e = (strain_raw >= ym_range[0]) & (strain_raw <= ym_range[1])
        if np.sum(mask_e) < 3: continue
            
        E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
        
        if apply_zeroing:
            shift = -intercept_y / E_slope
            strain = strain_raw - shift
            mask_pos = strain >= 0
            strain, stress = strain[mask_pos], stress_raw[mask_pos]
            f_final, d_final = df[f_col].values[mask_pos], disp_mm[mask_pos]
        else:
            strain, stress = strain_raw, stress_raw
            f_final, d_final = df[f_col].values, disp_mm

        # Yield & Energy
        offset_line = E_slope * (strain - 0.2)
        idx_yield = np.where((stress - offset_line) < 0)[0]
        y_stress = stress[idx_yield[0]] if len(idx_yield) > 0 else np.nan
        y_strain = strain[idx_yield[0]] if len(idx_yield) > 0 else np.nan
        
        try: work_j = np.trapezoid(f_final, d_final / 1000.0)
        except: work_j = np.trapz(f_final, d_final / 1000.0)
        toughness = (work_j / ((area * gauge_length) * 1e-9)) / 1e6

        all_results.append({
            "Sample": file.name,
            "Raw Column Force": f_col,
            "Raw Column Disp": d_col,
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
    fig.update_layout(
        xaxis_title="Corrected Engineering Strain (%)",
        yaxis_title="Engineering Stress (MPa)",
        template="plotly_white",
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    if all_results:
        res_df = pd.DataFrame(all_results)
        st.subheader("📊 Statistical Analysis")
        stats_df = res_df.drop(columns=['Sample', 'Raw Column Force', 'Raw Column Disp']).agg(['mean', 'std']).T
        st.table(stats_df.style.format("{:.2f}"))

        # --- EXCEL REPORT WITH GRAPHS ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Detailed Data', index=False)
            stats_df.to_excel(writer, sheet_name='Statistical Summary')
            
            # Create a separate sheet for Graphs
            workbook = writer.book
            worksheet_graph = workbook.add_worksheet('Analysis Graphs')
            chart = workbook.add_chart({'type': 'scatter', 'subtype': 'smooth'})
            
            # Add stress-strain chart (logic for the first sample for demo)
            worksheet_graph.write('A1', 'Note: Interactive graphs are in the Streamlit App. This sheet is for summary storage.')
            
            # Formatting
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            writer.sheets['Detailed Data'].set_column('A:K', 20)

        st.download_button(
            label="📥 Download Multi-Sheet Research Report",
            data=output.getvalue(),
            file_name=f"{project_name}_Full_Report.xlsx"
        )
