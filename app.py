import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io
import re
import requests

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Tensile Suite", layout="wide")

# --- 2. Professional Logo & Header ---
logo_url = "https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png"

col_logo, col_text = st.columns([1, 5])

with col_logo:
    try:
        st.image(logo_url, width=150) 
    except:
        st.header("🔬")

with col_text:
    st.title("Solomon Tensile Suite 2")
    st.markdown("""
    **Analytical Framework for Bio-Composite Strain Behavior** 🚀
    """)

# --- 3. Sidebar: Professional Inputs ---
st.sidebar.header("📝 Project Metadata")
project_name = st.sidebar.text_input("Research Topic", "PBAT-PLA-Biocomposites")

st.sidebar.header("📏 Specimen Geometry")
thickness = st.sidebar.number_input("Thickness (mm)", value=4.0, step=0.1)
width = st.sidebar.number_input("Width (mm)", value=4.0, step=0.1)
gauge_length = st.sidebar.number_input("Initial Gauge Length (L0) [mm]", value=25.0, step=1.0)
area = width * thickness 

st.sidebar.header("⚙️ Data Calibration")
unit_input = st.sidebar.selectbox("Raw Displacement Unit", ["Millimeters (mm)", "Micrometers (um)", "Meters (m)"])
scale_map = {"Millimeters (mm)": 1.0, "Micrometers (um)": 0.001, "Meters (m)": 1000.0}
u_scale = scale_map[unit_input]

apply_zeroing = st.sidebar.checkbox("Apply Toe-Compensation (Shift to 0,0)", value=True)

# --- 4. Unified Robust Data Loader ---
def smart_load(file):
    try:
        ext = file.name.split('.')[-1].lower()
        if ext == 'xlsx':
            # Uses openpyxl to read modern Excel files
            return pd.read_excel(file, engine='openpyxl')
        
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
    except Exception as e:
        st.error(f"Error loading {file.name}: {e}")
        return None

# --- 5. Main Engine ---
uploaded_files = st.file_uploader(
    "Upload Samples", 
    type=['csv', 'xlsx', 'txt'], 
    accept_multiple_files=True
)

if uploaded_files:
    all_results = []
    fig_main = go.Figure()

    # --- Bulk Update Logic ---
    st.subheader("🛠️ Sample Configuration & Modulus Validation")
    with st.expander("⚡ Bulk Update (Apply to All Samples)"):
        b1, b2 = st.columns([3, 1])
        bulk_range = b1.slider("Select Global Modulus Range (%)", 0.0, 10.0, (0.2, 1.0))
        if b2.button("Apply to All"):
            for file in uploaded_files:
                st.session_state[f"range_{file.name}"] = bulk_range
            st.rerun()

    sample_configs = {}

    for file in uploaded_files:
        df = smart_load(file)
        if df is None or df.empty: continue
        
        # 1. Engineering Conversion (Pre-process for the mini-plot)
        cols = df.columns.tolist()
        f_col_key = f"f_{file.name}"
        d_col_key = f"d_{file.name}"
        
        f_col = st.sidebar.selectbox(f"Force Col ({file.name})", cols, index=0, key=f_col_key)
        d_col = st.sidebar.selectbox(f"Disp Col ({file.name})", cols, index=1, key=d_col_key)
        
        df_clean = df[[f_col, d_col]].apply(pd.to_numeric, errors='coerce').dropna()
        disp_mm = df_clean[d_col].values * u_scale
        stress_raw = df_clean[f_col].values / area
        strain_raw = (disp_mm / gauge_length) * 100

        # --- Dynamic Per-Sample UI with Integrated Preview ---
        with st.expander(f"Adjust & Preview: {file.name}", expanded=False):
            ctrl_col, prev_col = st.columns([1, 2])
            
            # Controls
            current_range = ctrl_col.slider(
                "Modulus Fit Range (%)", 0.0, 10.0, (0.2, 1.0), key=f"range_{file.name}"
            )
            sample_configs[file.name] = current_range
            
            # Calculations for current sample
            mask_e = (strain_raw >= current_range[0]) & (strain_raw <= current_range[1])
            if np.sum(mask_e) >= 3:
                E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
                
                # Toe-Compensation for plotting
                if apply_zeroing:
                    shift = -intercept_y / E_slope
                    strain_plot = strain_raw - shift
                    mask_pos = strain_plot >= 0
                    strain_plot, stress_plot = strain_plot[mask_pos], stress_raw[mask_pos]
                    f_final = df_clean[f_col].values[mask_pos]
                    d_final = disp_mm[mask_pos]
                else:
                    strain_plot, stress_plot = strain_raw, stress_raw
                    f_final, d_final = df_clean[f_col].values, disp_mm

                # Mini Preview Plot
                fig_mini = go.Figure()
                fig_mini.add_trace(go.Scatter(x=strain_plot, y=stress_plot, name="Data", line=dict(color='teal')))
                
                fit_x = np.linspace(0, current_range[1] * 2, 20)
                fit_y = E_slope * fit_x + (0 if apply_zeroing else intercept_y)
                fig_mini.add_trace(go.Scatter(x=fit_x, y=fit_y, name="Fit", line=dict(dash='dot', color='red')))
                
                fig_mini.update_layout(
                    height=250, margin=dict(l=0, r=0, t=0, b=0),
                    xaxis_title="Strain (%)", yaxis_title="Stress (MPa)",
                    xaxis_range=[0, current_range[1] * 2.5], template="plotly_white", showlegend=False
                )
                prev_col.plotly_chart(fig_mini, use_container_width=True)

                # Final Metrics for results table
                offset_line = E_slope * (strain_plot - 0.2)
                idx_yield = np.where((stress_plot - offset_line) < 0)[0]
                y_stress = stress_plot[idx_yield[0]] if len(idx_yield) > 0 else np.nan
                y_strain = strain_plot[idx_yield[0]] if len(idx_yield) > 0 else np.nan
                
                try: work_j = np.trapezoid(f_final, d_final / 1000.0)
                except: work_j = np.trapz(f_final, d_final / 1000.0)
                
                all_results.append({
                    "Sample": file.name,
                    "Modulus (E) [MPa]": round(E_slope * 100, 1),
                    "Yield Stress [MPa]": round(y_stress, 2),
                    "Yield Strain [%]": round(y_strain, 2),
                    "Stress @ Break [MPa]": round(stress_plot[-1], 2),
                    "Strain @ Break [%]": round(strain_plot[-1], 2),
                    "Work Done [J]": round(work_j, 4),
                    "Toughness [MJ/m³]": round((work_j / (area * gauge_length * 1e-9)) / 1e6, 3)
                })
                
                fig_main.add_trace(go.Scatter(x=strain_plot, y=stress_plot, name=file.name))
            else:
                ctrl_col.error("Insufficient points in range.")

    # --- 6. Final Reporting Dashboard ---
   # --- Updated Excel Export with Specimen Count (n=X) ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 1. Individual Sample Results Sheet
            res_df.to_excel(writer, sheet_name='Individual_Samples', index=False)
            
            # 2. Batch Summary Statistics Sheet
            # Calculate Mean, SD, and Count (n)
            stats_summary = res_df.drop(columns='Sample').agg(['mean', 'std', 'count']).T
            # Rename 'count' to 'Specimen Count (n)' for professional clarity
            stats_summary.columns = ['Mean', 'Std. Deviation', 'Specimen Count (n)']
            
            stats_summary.to_excel(writer, sheet_name='Batch_Statistics')
            
            # Formatting for professional report
            workbook = writer.book
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            num_format = workbook.add_format({'num_format': '0.00', 'border': 1})
            
            for sheet_name in ['Individual_Samples', 'Batch_Statistics']:
                worksheet = writer.sheets[sheet_name]
                # Auto-adjust column width for readability
                worksheet.set_column('A:Z', 22, num_format)
                
        st.download_button(
            label=f"📥 Download Official Report (n={len(res_df)})", 
            data=output.getvalue(), 
            file_name=f"{project_name}_Final_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Click to download the Excel report containing individual data, means, and standard deviations."
        )
