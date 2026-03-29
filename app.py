import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import re
import requests
from PIL import Image
from streamlit_drawable_canvas import st_canvas

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
    st.markdown("""**Analytical Framework for Bio-Composite Strain Behavior** 🚀""")

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

# --- NEW: Visual Customization ---
st.sidebar.header("🎨 Plot Customization")
line_thickness = st.sidebar.slider("Line Thickness (Journal Plot)", 0.5, 5.0, 2.5, 0.5)

# --- 4. Digitizer Helper Class ---
class DigitizedFile:
    def __init__(self, name, df):
        self.name = name
        self.df = df
    def getvalue(self): return None 

# --- 5. Image Digitizer Module ---
def image_digitizer_ui():
    st.subheader("🖼️ Plot Digitizer Mode")
    digitizer_file = st.file_uploader("Upload Plot Image", type=["png", "jpg", "jpeg"], key="digitizer_upload")
    if digitizer_file:
        img = Image.open(digitizer_file)
        c1, c2 = st.columns([2, 1])
        with c2:
            st.info("Instructions:\n1. Origin (0,0)\n2. Max X Point\n3. Max Y Point\n4. Trace Curve")
            real_max_x = st.number_input("Real Max Strain (%)", value=10.0)
            real_max_y = st.number_input("Real Max Stress (MPa)", value=100.0)
        with c1:
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#ff0000",
                background_image=img, height=img.height * (800 / img.width), width=800,
                drawing_mode="point", key="canvas_digitizer",
            )
        if canvas_result.json_data is not None:
            df_points = pd.json_normalize(canvas_result.json_data["objects"])
            if len(df_points) >= 4:
                coords = df_points[['left', 'top']].values
                origin, mX, mY = coords[0], coords[1], coords[2]
                curve = coords[3:]
                sX = real_max_x / (mX[0] - origin[0])
                sY = real_max_y / (origin[1] - mY[1])
                data = [{"Digitized Strain": (p[0]-origin[0])*sX, "Digitized Stress": (origin[1]-p[1])*sY} for p in curve]
                return DigitizedFile(f"Digitized_{digitizer_file.name}", pd.DataFrame(data))
    return None

# --- 6. Unified Robust Data Loader ---
def smart_load(file):
    if hasattr(file, 'df'): return file.df 
    try:
        ext = file.name.split('.')[-1].lower()
        if ext == 'xlsx': return pd.read_excel(file, engine='openpyxl')
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

# --- 7. Main Engine Input Selector ---
input_mode = st.radio("Select Input Source", ["Standard Files (CSV/XLSX)", "Image Digitizer"], horizontal=True)
if input_mode == "Image Digitizer":
    d_file = image_digitizer_ui()
    uploaded_files = [d_file] if d_file else []
else:
    uploaded_files = st.file_uploader("Upload Samples", type=['csv', 'xlsx', 'txt'], accept_multiple_files=True, key="main_loader")

# --- 8. Core Processing Engine ---
if uploaded_files:
    all_results = []
    plot_data_storage = {} 

    st.subheader("🛠️ Sample Configuration & Modulus Validation")
    with st.expander("⚡ Bulk Update (Apply to All Samples)"):
        b1, b2 = st.columns([3, 1])
        bulk_range = b1.slider("Select Global Modulus Range (%)", 0.0, 20.0, (0.2, 1.0), key="bulk_slider")
        if b2.button("Apply to All"):
            for file in uploaded_files:
                if file: st.session_state[f"range_{file.name}"] = bulk_range
            st.rerun()

    for file in uploaded_files:
        if file is None: continue
        df = smart_load(file)
        if df is None or df.empty: continue
        
        cols = df.columns.tolist()
        inst_stress_col = next((c for c in cols if "sforzo" in c.lower()), None)
        def_f = inst_stress_col if inst_stress_col else (cols[1] if "Digitized Stress" in cols else cols[0])
        def_d = cols[0] if "Digitized Strain" in cols else cols[1]

        f_col = st.sidebar.selectbox(f"Force/Stress ({file.name})", cols, index=cols.index(def_f), key=f"f_{file.name}")
        d_col = st.sidebar.selectbox(f"Disp/Strain ({file.name})", cols, index=cols.index(def_d), key=f"d_{file.name}")
        
        df_clean = df[[f_col, d_col]].apply(pd.to_numeric, errors='coerce').dropna()
        
        if "Digitized" in str(file.name):
            stress_all = df_clean[f_col].values
            strain_all = df_clean[d_col].values
            disp_all = (strain_all / 100) * gauge_length
        else:
            disp_all = df_clean[d_col].values * u_scale
            stress_all = df_clean[f_col].values if (inst_stress_col and f_col == inst_stress_col) else (df_clean[f_col].values / area)
            strain_all = (disp_all / gauge_length) * 100

        peak_idx = np.argmax(stress_all)
        stress_raw = stress_all[:peak_idx + 1]
        strain_raw = strain_all[:peak_idx + 1]

        with st.expander(f"Adjust & Preview: {file.name}", expanded=False):
            ctrl_col, prev_col = st.columns([1, 2])
            current_range = ctrl_col.slider("Modulus Fit Range (%)", 0.0, 20.0, (0.2, 1.0), key=f"range_{file.name}")
            mask_e = (strain_raw >= current_range[0]) & (strain_raw <= current_range[1])
            
            if np.sum(mask_e) >= 3:
                E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
                if apply_zeroing:
                    shift = -intercept_y / E_slope
                    strain_plot = strain_raw - shift
                    mask_pos = strain_plot >= 0
                    strain_plot, stress_plot = strain_plot[mask_pos], stress_raw[mask_pos]
                else:
                    strain_plot, stress_plot = strain_raw, stress_raw

                plot_data_storage[file.name] = (strain_plot, stress_plot)

                fig_mini = go.Figure()
                fig_mini.add_trace(go.Scatter(x=strain_plot, y=stress_plot, name="Data", line=dict(color='teal')))
                fig_mini.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), template="plotly_white", showlegend=False)
                prev_col.plotly_chart(fig_mini, use_container_width=True)

                # Advanced Analytics
                offset_line = E_slope * (strain_plot - 0.2)
                idx_yield = np.where((stress_plot - offset_line) < 0)[0]
                y_stress = stress_plot[idx_yield[0]] if len(idx_yield) > 0 else np.nan
                y_strain = strain_plot[idx_yield[0]] if len(idx_yield) > 0 else np.nan
                
                f_final = stress_plot * area
                d_final_m = (strain_plot / 100 * gauge_length) / 1000.0
                try: work_j = np.trapezoid(f_final, d_final_m)
                except: work_j = np.trapz(f_final, d_final_m)
                
                toughness = (work_j / (area * gauge_length * 1e-9)) / 1e6

                all_results.append({
                    "Sample": file.name, 
                    "Modulus (E) [MPa]": round(E_slope * 100, 1),
                    "Yield Stress [MPa]": round(y_stress, 2),
                    "Yield Strain [%]": round(y_strain, 2),
                    "Stress @ Peak [MPa]": round(stress_plot[-1], 2), 
                    "Strain @ Peak [%]": round(strain_plot[-1], 2),
                    "Work Done [J]": round(work_j, 4),
                    "Toughness [MJ/m³]": round(toughness, 3)
                })
            else:
                ctrl_col.error("Insufficient points.")

    # --- 9. Final Reports & Visualizations ---
    if all_results:
        res_df = pd.DataFrame(all_results)
        st.divider()
        
        view_mode = st.radio("Select Visualization Mode", ["Interactive (Cursor Inspection)", "Static (High-Res Journal TIFF)"], horizontal=True)

        if view_mode == "Interactive (Cursor Inspection)":
            fig_main = go.Figure()
            for name, data in plot_data_storage.items():
                fig_main.add_trace(go.Scatter(x=data[0], y=data[1], name=name, mode='lines', hovertemplate='Strain: %{x:.2f}%<br>Stress: %{y:.2f} MPa'))
            
            fig_main.update_layout(
                template="simple_white",
                xaxis=dict(title="Strain (%)", range=[0, None], mirror=True, ticks='inside', showline=True, linecolor='black', linewidth=2),
                yaxis=dict(title="Stress (MPa)", range=[0, None], mirror=True, ticks='inside', showline=True, linecolor='black', linewidth=2),
                hovermode="x unified", height=600
            )
            st.plotly_chart(fig_main, use_container_width=True)

        else:
            # --- JOURNAL QUALITY STATIC PLOT ---
            plt.rcParams.update({
                "font.family": "serif", 
                "font.serif": ["Times New Roman"], 
                "font.size": 12, 
                "axes.linewidth": 1.5,
                "xtick.direction": "in",
                "ytick.direction": "in"
            })
            
            fig, ax = plt.subplots(figsize=(8, 6))
            journal_colors = ['#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
            
            for i, (name, data) in enumerate(plot_data_storage.items()):
                color = journal_colors[i % len(journal_colors)]
                # Applied sidebar line_thickness slider here
                ax.plot(data[0], data[1], label=name, color=color, linestyle='-', lw=line_thickness)
            
            ax.set_xlim(left=0); ax.set_ylim(bottom=0)
            ax.set_xlabel('Strain (%)', fontweight='bold', labelpad=10)
            ax.set_ylabel('Stress (MPa)', fontweight='bold', labelpad=10)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.grid(True, linestyle='--', alpha=0.3)
            ax.legend(frameon=False, loc='lower right', fontsize=10)
            
            st.pyplot(fig)
            
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format="tiff", dpi=300, bbox_inches='tight')
            st.download_button(label="🖼️ Download Journal TIFF (300 DPI)", data=img_buffer.getvalue(), file_name=f"{project_name}_Journal.tiff")

        # --- 10. Batch Comparison Section ---
        st.divider()
        st.subheader("⚖️ Batch Property Comparison")
        col_comp1, col_comp2 = st.columns([1, 2])
        control_sample = col_comp1.selectbox("Select Control Sample (Baseline)", res_df["Sample"].tolist())
        
        if control_sample:
            baseline = res_df[res_df["Sample"] == control_sample].iloc[0]
            comp_df = res_df.copy()
            
            comp_df["Modulus Δ (%)"] = ((comp_df["Modulus (E) [MPa]"] - baseline["Modulus (E) [MPa]"]) / baseline["Modulus (E) [MPa]"]) * 100
            comp_df["Strength Δ (%)"] = ((comp_df["Stress @ Peak [MPa]"] - baseline["Stress @ Peak [MPa]"]) / baseline["Stress @ Peak [MPa]"]) * 100
            comp_df["Toughness Δ (%)"] = ((comp_df["Toughness [MJ/m³]"] - baseline["Toughness [MJ/m³]"]) / baseline["Toughness [MJ/m³]"]) * 100
            
            st.dataframe(
                comp_df[["Sample", "Modulus (E) [MPa]", "Modulus Δ (%)", "Stress @ Peak [MPa]", "Strength Δ (%)", "Toughness [MJ/m³]", "Toughness Δ (%)"]].style.format({
                    "Modulus Δ (%)": "{:+.1f}%",
                    "Strength Δ (%)": "{:+.1f}%",
                    "Toughness Δ (%)": "{:+.1f}%"
                }).background_gradient(subset=["Modulus Δ (%)", "Strength Δ (%)", "Toughness Δ (%)"], cmap="RdYlGn"),
                hide_index=True, use_container_width=True
            )

        # --- 11. Individual Results & Summary ---
        st.divider()
        st.subheader(f"📊 Batch Summary Statistics (n={len(res_df)})")
        stats_df = res_df.drop(columns='Sample').agg(['mean', 'std', 'count']).T
        stats_df.columns = ['Mean', 'Std. Deviation', 'n']
        st.table(stats_df.style.format("{:.2f}"))
        
        st.subheader("📋 Complete Individual Test Records")
        st.dataframe(res_df[[
            "Sample", "Modulus (E) [MPa]", "Yield Stress [MPa]", "Yield Strain [%]", 
            "Stress @ Peak [MPa]", "Strain @ Peak [%]", "Work Done [J]", "Toughness [MJ/m³]"
        ]], hide_index=True, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Samples', index=False)
            stats_df.to_excel(writer, sheet_name='Stats')
            if control_sample:
                comp_df.to_excel(writer, sheet_name='Comparison_Analysis', index=False)
        
        st.download_button(label="📥 Download Full Excel Report", data=output.getvalue(), file_name=f"{project_name}_Full_Report.xlsx")
