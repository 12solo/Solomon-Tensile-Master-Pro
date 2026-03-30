import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import io
import re
import requests
import base64
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# --- 1. Page Configuration & Custom Font Styling ---
st.set_page_config(page_title="Solomon Tensile Suite", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="css"], .stMarkdown, .stText, .stButton, .stSelectbox, .stTable {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }
    </style>
    """, unsafe_allow_html=True)

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

st.sidebar.header("🎨 Plot Customization")
line_thickness = st.sidebar.slider("Line Thickness (Journal Plot)", 0.5, 5.0, 2.5, 0.5)
legend_pos = st.sidebar.selectbox("Legend Position", ["lower right", "upper right", "upper left", "lower left", "best", "outside"], index=0)

auto_scale = st.sidebar.checkbox("Enable Auto-Scale", value=True)
if not auto_scale:
    custom_x_max = st.sidebar.number_input("Manual X Max (Strain %)", value=100.0)
    custom_y_max = st.sidebar.number_input("Manual Y Max (Stress MPa)", value=50.0)

# --- NEW: Zoom Parameters for Matplotlib Inset ---
st.sidebar.header("🔍 Zoom Inset Setup")
inset_x = st.sidebar.slider("Inset Horizontal (X)", 0.0, 0.8, 0.55, 0.05)
inset_y = st.sidebar.slider("Inset Vertical (Y)", 0.0, 0.8, 0.05, 0.05)
inset_w = st.sidebar.slider("Inset Width", 0.2, 0.6, 0.40, 0.05)
inset_h = st.sidebar.slider("Inset Height", 0.2, 0.6, 0.40, 0.05)

def clean_label(name):
    return re.sub(r'\.(txt|csv|xlsx|xls)$', '', name, flags=re.IGNORECASE)

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
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        
        c1, c2 = st.columns([2, 1])
        with c2:
            st.info("Instructions:\n1. Origin (0,0)\n2. Max X Point\n3. Max Y Point\n4. Trace Curve")
            real_max_x = st.number_input("Real Max Strain (%)", value=10.0)
            real_max_y = st.number_input("Real Max Stress (MPa)", value=100.0)
        with c1:
            h_calc = int(img.height * (800 / img.width))
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)", 
                stroke_width=2, 
                stroke_color="#ff0000",
                background_image=Image.open(digitizer_file),
                height=h_calc, 
                width=800,
                drawing_mode="point", 
                key="canvas_digitizer",
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
    modulus_fit_storage = {} 
    yield_point_storage = {} # Store yield points for markers

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
            custom_name = st.text_input("Scientific Display Name", value=clean_label(file.name), key=f"name_{file.name}")
            ctrl_col, prev_col = st.columns([1, 2])
            current_range = ctrl_col.slider("Modulus Fit Range (%)", 0.0, 20.0, (0.2, 1.0), key=f"range_{file.name}")
            mask_e = (strain_raw >= current_range[0]) & (strain_raw <= current_range[1])
            
            if np.sum(mask_e) >= 3:
                E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
                
                if apply_zeroing:
                    shift = -intercept_y / E_slope
                    strain_plot = strain_raw - shift
                    mask_pos = (strain_plot >= 0)
                    strain_plot, stress_plot = strain_plot[mask_pos], stress_raw[mask_pos]
                else:
                    strain_plot, stress_plot = strain_raw, stress_raw

                plot_data_storage[custom_name] = (strain_plot, stress_plot)
                fit_x = np.linspace(0, current_range[1] * 2, 20)
                fit_y = E_slope * fit_x + (0 if apply_zeroing else intercept_y)
                modulus_fit_storage[custom_name] = (fit_x, fit_y)

                # --- YIELD DETECTION & MATERIAL CLASS ---
                offset_line = E_slope * (strain_plot - 0.2)
                idx_yield = np.where(stress_plot < offset_line)[0]
                
                if len(idx_yield) > 0:
                    y_stress = round(stress_plot[idx_yield[0]], 2)
                    y_strain = round(strain_plot[idx_yield[0]], 2)
                    mat_class = "Ductile"
                    yield_point_storage[custom_name] = (y_strain, y_stress)
                else:
                    y_stress = "N/A"
                    y_strain = "N/A"
                    mat_class = "Brittle"
                    yield_point_storage[custom_name] = (None, None)

                fig_mini = go.Figure()
                fig_mini.add_trace(go.Scatter(x=strain_plot, y=stress_plot, name="Data", line=dict(color='#1f77b4')))
                fig_mini.add_trace(go.Scatter(x=fit_x, y=fit_y, name="Fit", line=dict(dash='dot', color='#d62728')))
                if mat_class == "Ductile":
                    fig_mini.add_trace(go.Scatter(x=[y_strain], y=[y_stress], mode='markers', marker=dict(size=10, color='#2ca02c'), name="Yield"))
                fig_mini.update_layout(height=250, margin=dict(l=0, r=0, t=0, b=0), template="plotly_white", showlegend=False)
                prev_col.plotly_chart(fig_mini, use_container_width=True)

                try: work_j = np.trapezoid(stress_plot * area, (strain_plot/100 * gauge_length) / 1000.0)
                except: work_j = np.trapz(stress_plot * area, (strain_plot/100 * gauge_length) / 1000.0)
                
                all_results.append({
                    "Sample": custom_name, "Class": mat_class,
                    "Modulus (E) [MPa]": round(E_slope * 100, 1),
                    "Yield Stress [MPa]": y_stress, "Yield Strain [%]": y_strain,
                    "Stress @ Peak [MPa]": round(stress_plot[-1], 2), "Strain @ Peak [%]": round(strain_plot[-1], 2),
                    "Work Done [J]": round(work_j, 4), "Toughness [MJ/m³]": round((work_j / (area * gauge_length * 1e-9)) / 1e6, 3)
                })
            else:
                ctrl_col.error("Insufficient points.")

    # --- 9. Final Reports & Visualizations ---
    if all_results:
        res_df = pd.DataFrame(all_results)
        st.divider()
        view_mode = st.radio("Select Visualization Mode", ["Interactive (Cursor Inspection)", "Static (High-Res Journal TIFF)"], horizontal=True)

        distinct_20 = [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', 
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5', 
            '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
        ]

        if view_mode == "Interactive (Cursor Inspection)":
            fig_main = go.Figure()
            for i, (name, data) in enumerate(plot_data_storage.items()):
                color = distinct_20[i % 20]
                fig_main.add_trace(go.Scatter(
                    x=data[0], y=data[1], name=name, 
                    mode='lines', line=dict(width=line_thickness, color=color),
                    hovertemplate='<b>%{fullData.name}</b><br>Strain: %{x:.2f}%<br>Stress: %{y:.2f} MPa<extra></extra>'
                ))
                # Add Yield Point for Interactive
                ys, yst = yield_point_storage[name]
                if ys:
                    fig_main.add_trace(go.Scatter(x=[ys], y=[yst], mode='markers', marker=dict(color='#2ca02c', size=8, line=dict(width=1, color='black')), name=f"Yield: {name}", showlegend=False))
            
            x_lim = res_df["Strain @ Peak [%]"].max() * 1.05 if auto_scale else custom_x_max
            y_lim = res_df["Stress @ Peak [MPa]"].max() * 1.1 if auto_scale else custom_y_max
            fig_main.update_layout(template="simple_white", xaxis=dict(title="Strain (%)", range=[0, x_lim], mirror=True, ticks='inside', showline=True, linecolor='black', linewidth=2), yaxis=dict(title="Stress (MPa)", range=[0, y_lim], mirror=True, ticks='inside', showline=True, linecolor='black', linewidth=2), hovermode="closest", height=650)
            st.plotly_chart(fig_main, use_container_width=True)

        else:
            plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman"], "font.size": 12, "axes.linewidth": 1.5, "xtick.direction": "in", "ytick.direction": "in"})
            fig, ax = plt.subplots(figsize=(9, 7))
            
            # MAIN PLOT
            for i, (name, data) in enumerate(plot_data_storage.items()):
                color = distinct_20[i % 20]
                ax.plot(data[0], data[1], label=name, color=color, linestyle='-', lw=line_thickness)
                
                # --- ADD YIELD POINT MARKERS ---
                ys, yst = yield_point_storage[name]
                if ys:
                    ax.plot(ys, yst, 'o', color='#2ca02c', markersize=8, markeredgecolor='black', zorder=6)
            
            if auto_scale:
                ax.set_xlim(0, res_df["Strain @ Peak [%]"].max() * 1.05)
                ax.set_ylim(0, res_df["Stress @ Peak [MPa]"].max() * 1.1)
            else:
                ax.set_xlim(0, custom_x_max); ax.set_ylim(0, custom_y_max)

            ax.set_xlabel('Strain (%)', fontweight='bold'); ax.set_ylabel('Stress (MPa)', fontweight='bold')
            ax.spines['top'].set_visible(True); ax.spines['right'].set_visible(True)
            ax.grid(True, linestyle='--', alpha=0.5)
            
            if legend_pos == "outside": ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True, shadow=True, fontsize=9)
            else: ax.legend(loc=legend_pos, frameon=True, shadow=True, fontsize=9)
            
            # --- INSET ZOOM LOGIC ---
            axins = ax.inset_axes([inset_x, inset_y, inset_w, inset_h])
            for i, (name, data) in enumerate(plot_data_storage.items()):
                color = distinct_20[i % 20]
                axins.plot(data[0], data[1], color=color, lw=line_thickness*0.8)
                ys, yst = yield_point_storage[name]
                if ys:
                    axins.plot(ys, yst, 'o', color='#2ca02c', markersize=6, markeredgecolor='black')
            
            # Set Inset limits based on Yield/Modulus range
            max_y_strain = pd.to_numeric(res_df["Yield Strain [%]"], errors='coerce').max()
            z_lim = max(2.5, (max_y_strain + 1.5) if not np.isnan(max_y_strain) else 2.5)
            axins.set_xlim(0, z_lim)
            axins.set_ylim(0, res_df["Stress @ Peak [MPa]"].max() * 0.5) # Focus on the early region
            ax.indicate_inset_zoom(axins, edgecolor="black")
            
            st.pyplot(fig)
            img_buffer = io.BytesIO(); fig.savefig(img_buffer, format="tiff", dpi=300, bbox_inches='tight')
            st.download_button(label="🖼️ Download Journal TIFF (300 DPI)", data=img_buffer.getvalue(), file_name=f"{project_name}_Analysis.tiff", key="journal_tiff_btn")

        # --- 10. Batch Comparison ---
        st.divider()
        st.subheader("⚖️ Batch Property Comparison")
        col_comp1, col_comp2 = st.columns([1, 2])
        control_sample = col_comp1.selectbox("Select Control Sample (Baseline)", res_df["Sample"].tolist(), key="baseline_selector_final")
        
        if control_sample:
            baseline = res_df[res_df["Sample"] == control_sample].iloc[0]
            comp_df = res_df.copy()
            for col in ["Modulus (E) [MPa]", "Stress @ Peak [MPa]", "Toughness [MJ/m³]"]:
                comp_df[f"{col.split(' ')[0]} Δ (%)"] = pd.to_numeric(comp_df[col], errors='coerce')
                b_val = pd.to_numeric(baseline[col], errors='coerce')
                comp_df[f"{col.split(' ')[0]} Δ (%)"] = ((comp_df[f"{col.split(' ')[0]} Δ (%)"] - b_val) / b_val) * 100
            
            delta_cols = [c for c in comp_df.columns if "Δ" in c]
            st.dataframe(comp_df[["Sample", "Class", "Modulus (E) [MPa]", "Modulus Δ (%)", "Stress @ Peak [MPa]", "Strength Δ (%)", "Toughness [MJ/m³]", "Toughness Δ (%)"]].style.format("{:+.1f}%", subset=delta_cols).background_gradient(subset=delta_cols, cmap="RdYlGn"), hide_index=True, use_container_width=True)

        # --- 11. Statistics & Individual Records ---
        st.divider()
        st.subheader(f"📊 Batch Summary Statistics (n={len(res_df)})")
        numeric_res = res_df.apply(pd.to_numeric, errors='coerce').drop(columns=['Sample', 'Class'], errors='ignore')
        st.table(numeric_res.agg(['mean', 'std', 'count']).T.style.format("{:.2f}"))

        st.subheader("📋 Complete Individual Test Records")
        st.dataframe(res_df[["Sample", "Class", "Modulus (E) [MPa]", "Yield Stress [MPa]", "Yield Strain [%]", "Stress @ Peak [MPa]", "Strain @ Peak [%]", "Work Done [J]", "Toughness [MJ/m³]"]], hide_index=True, use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Samples', index=False)
        st.download_button(label="📥 Download Full Excel Report", data=output.getvalue(), file_name=f"{project_name}_Full_Report.xlsx", key="full_excel_report_btn")
