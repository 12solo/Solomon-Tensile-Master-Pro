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
from streamlit_drawable_canvas import st_canvas

# --- 4b. Image Digitizer Module ---
def image_digitizer_ui():
    st.subheader("🖼️ Plot Digitizer Mode")
    digitizer_file = st.file_uploader("Upload Image/Plot to Digitize", type=["png", "jpg", "jpeg"])
    
    if digitizer_file:
        img = Image.open(digitizer_file)
        
        col_img, col_ctrl = st.columns([2, 1])
        
        with col_ctrl:
            st.info("1. Click Origin (0,0)\n2. Click Max X\n3. Click Max Y\n4. Trace Curve")
            real_max_x = st.number_input("Real Max Strain (%)", value=10.0)
            real_max_y = st.number_input("Real Max Stress (MPa)", value=100.0)
            
        with col_img:
            # The Canvas for clicking
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=2,
                stroke_color="#ff0000",
                background_image=img,
                update_streamlit=True,
                height=img.height * (800 / img.width), # Responsive scaling
                width=800,
                drawing_mode="point",
                key="canvas",
            )

        if canvas_result.json_data is not None:
            df_points = pd.json_normalize(canvas_result.json_data["objects"])
            if not df_points.empty:
                # Coordinate Transformation Logic
                coords = df_points[['left', 'top']].values
                if len(coords) >= 3:
                    origin = coords[0]
                    max_x_px = coords[1]
                    max_y_px = coords[2]
                    curve_points = coords[3:]
                    
                    # Math for conversion
                    scale_x = real_max_x / (max_x_px[0] - origin[0])
                    scale_y = real_max_y / (origin[1] - max_y_px[1])
                    
                    digitized_data = []
                    for p in curve_points:
                        strain = (p[0] - origin[0]) * scale_x
                        stress = (origin[1] - p[1]) * scale_y
                        digitized_data.append({"Strain (%)": strain, "Stress (MPa)": stress})
                    
                    new_df = pd.DataFrame(digitized_data)
                    st.success(f"Digitized {len(new_df)} points!")
                    return new_df, f"Digitized_{digitizer_file.name}"
    return None, None

# --- Add this inside Section 5 (Main Engine) ---
# Replace your current 'uploaded_files' logic with a toggle
mode = st.radio("Input Mode", ["File Upload", "Image Digitizer"], horizontal=True)

if mode == "Image Digitizer":
    d_df, d_name = image_digitizer_ui()
    if d_df is not None:
        # We manually create a 'file-like' object to trick your engine
        uploaded_files = [type('UploadedFile', (object,), {'name': d_name, 'getvalue': lambda: d_df, 'df': d_df})]
else:
    uploaded_files = st.file_uploader("Upload Samples", type=['csv', 'xlsx', 'txt'], accept_multiple_files=True)
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
        
        cols = df.columns.tolist()
        f_col_key = f"f_{file.name}"
        d_col_key = f"d_{file.name}"
        
        f_col = st.sidebar.selectbox(f"Force Col ({file.name})", cols, index=0, key=f_col_key)
        d_col = st.sidebar.selectbox(f"Disp Col ({file.name})", cols, index=1, key=d_col_key)
        
        df_clean = df[[f_col, d_col]].apply(pd.to_numeric, errors='coerce').dropna()
        disp_mm = df_clean[d_col].values * u_scale
        stress_raw = df_clean[f_col].values / area
        strain_raw = (disp_mm / gauge_length) * 100

        with st.expander(f"Adjust & Preview: {file.name}", expanded=False):
            ctrl_col, prev_col = st.columns([1, 2])
            current_range = ctrl_col.slider("Modulus Fit Range (%)", 0.0, 10.0, (0.2, 1.0), key=f"range_{file.name}")
            sample_configs[file.name] = current_range
            
            mask_e = (strain_raw >= current_range[0]) & (strain_raw <= current_range[1])
            if np.sum(mask_e) >= 3:
                E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
                
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

                fig_mini = go.Figure()
                fig_mini.add_trace(go.Scatter(x=strain_plot, y=stress_plot, name="Data", line=dict(color='teal')))
                fit_x = np.linspace(0, current_range[1] * 2, 20)
                fit_y = E_slope * fit_x + (0 if apply_zeroing else intercept_y)
                fig_mini.add_trace(go.Scatter(x=fit_x, y=fit_y, name="Fit", line=dict(dash='dot', color='red')))
                
                fig_mini.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), template="plotly_white", showlegend=False)
                prev_col.plotly_chart(fig_mini, use_container_width=True)

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
                ctrl_col.error("Insufficient points.")

   # --- 6. Results & Export (FIXED INDENTATION) ---
    if all_results:
        # This block must be indented
        res_df = pd.DataFrame(all_results)
        
        st.divider()
        st.subheader("Global Stress-Strain Comparison")
        fig_main.update_layout(
            xaxis_title="Strain (%)", 
            yaxis_title="Stress (MPa)", 
            template="plotly_white"
        )
        st.plotly_chart(fig_main, use_container_width=True)

        st.subheader(f"📊 Batch Summary Statistics (n={len(res_df)})")
        stats_df = res_df.drop(columns='Sample').agg(['mean', 'std', 'count']).T
        stats_df.columns = ['Mean', 'Std. Deviation', 'n']
        st.table(stats_df.style.format("{:.2f}"))
        st.dataframe(res_df, hide_index=True)

        # Excel Export logic
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Individual_Samples', index=False)
            stats_df.to_excel(writer, sheet_name='Batch_Statistics')
            
            workbook = writer.book
            for sheet_name in ['Individual_Samples', 'Batch_Statistics']:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:Z', 20)

        # Download button remains inside the IF block
        st.download_button(
            label=f"📥 Download Official Report (n={len(res_df)})", 
            data=output.getvalue(), 
            file_name=f"{project_name}_Final_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # Optional: Add a message if the list is empty
        st.warning("No valid results found. Please adjust your fitting ranges.")
