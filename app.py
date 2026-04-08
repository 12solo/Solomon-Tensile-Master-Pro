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

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Tensile Extrapolation Suite | Solomon Scientific",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# GLOBAL CSS — White Theme + Navy/Gold Headers & Clean UI
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
    --navy:       #0b1120;
    --navy-mid:   #111827;
    --gold:       #c9a84c;
    --gold-dim:   #9c7a32;
    --bg-white:   #ffffff;
    --bg-offwhite:#f8fafc;
    --text-dark:  #111827; 
    --text-muted: #64748b; 
    --border:     #e2e8f0;
    --radius:     4px;
    
    --font-head:  'Playfair Display', Georgia, serif;
    --font-mono:  'IBM Plex Mono', 'Courier New', monospace;
    --font-body:  'IBM Plex Sans', 'Segoe UI', sans-serif;
}

/* ── Reset & Base ─────────────────────────────── */
html, body, [class*="css"], .stMarkdown, .stText, .stButton, .stSelectbox, .stTable {
    font-family: var(--font-body) !important;
    color: var(--text-dark) !important;
}
.stApp {
    background: var(--bg-white) !important;
}

[data-testid="block-container"] {
    padding-top: 1.5rem !important; 
    padding-bottom: 2rem !important;
}

/* ── SURGICAL CLEAN UI (Hides Popups & Arrows & Shadows) ── */
#MainMenu { visibility: hidden !important; display: none !important; }
.stDeployButton { display: none !important; }
footer { visibility: hidden !important; display: none !important; }
header { background: transparent !important; box-shadow: none !important; } 

/* Hide "Press Enter to apply" */
div[data-testid="InputInstructions"] { display: none !important; visibility: hidden !important; opacity: 0 !important; height: 0px !important; }

/* Hide up/down arrows (steppers) on number inputs */
input[type="number"]::-webkit-inner-spin-button, 
input[type="number"]::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
input[type="number"] { -moz-appearance: textfield; }

/* Clean Uploader: Hide Cloud Icon and 200MB text */
[data-testid="stFileUploadDropzone"] svg { display: none !important; }
[data-testid="stFileUploadDropzone"] small { display: none !important; }
[data-testid="stFileUploadDropzone"] { padding: 1rem !important; }

/* Hide Hover Tooltips */
div[data-baseweb="tooltip"] { display: none !important; visibility: hidden !important; opacity: 0 !important; }
[data-testid="stTooltipHoverTarget"] { pointer-events: none !important; cursor: default !important; }

/* ── Sidebar ──────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-offwhite) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: var(--font-body) !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--gold-dim) !important;
    margin-top: 0.25rem !important;
}
[data-testid="stSidebar"] hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1rem 0 !important;
}

/* ── Inputs (Sidebar & Main) ──────────────────── */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] select,
.stSelectbox > div > div,
.stTextInput > div > div > input,
.stNumberInput > div > div > input {
    background: var(--bg-white) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    color: var(--text-dark) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.85rem !important;
    box-shadow: none !important;
}

[data-testid="stFileUploadDropzone"] {
    background: var(--bg-offwhite) !important;
    border: 1px dashed var(--border) !important;
    border-radius: var(--radius) !important;
}
[data-testid="stFileUploadDropzone"]:hover {
    border-color: var(--gold) !important;
}

/* ── Headings Main ────────────────────────────── */
h1, h2, h3 { color: var(--navy) !important; font-weight: 700 !important; }

/* ── Buttons ──────────────────────────────────── */
.stButton > button {
    background: var(--bg-offwhite) !important;
    color: var(--navy) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-body) !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    padding: 0.5rem 1.1rem !important;
    box-shadow: none !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: var(--border) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--gold-dim), var(--gold)) !important;
    color: var(--navy) !important;
    border: none !important;
}
[data-testid="stDownloadButton"] > button {
    background: var(--bg-offwhite) !important;
    color: var(--navy) !important;
    border: 1px solid var(--border) !important;
}

/* ── Expanders ────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    background: var(--bg-white) !important;
    box-shadow: none !important;
}
[data-testid="stExpander"] summary p {
    color: var(--navy) !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
}

/* ── DataFrames ───────────────────────────────── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    box-shadow: none !important;
}
[data-testid="stDataFrame"] th {
    background: var(--bg-offwhite) !important;
    color: var(--navy) !important;
    font-family: var(--font-body) !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
}
[data-testid="stDataFrame"] td {
    color: var(--text-dark) !important;
    background: var(--bg-white) !important;
    font-family: var(--font-mono) !important;
}

/* ── Alerts / Info ────────────────────────────── */
[data-testid="stAlert"] {
    background: rgba(201, 168, 76, 0.1) !important;
    border: 1px solid rgba(201, 168, 76, 0.3) !important;
    border-radius: var(--radius) !important;
    color: var(--text-dark) !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# HEADER & SIDEBAR RENDERING (From Batch App)
# ==========================================
def get_base64(path):
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return None

def render_header():
    logo_path = "LOGO.png"
    img_b64 = get_base64(logo_path)
    if img_b64:
        icon_html = f'<img src="data:image/png;base64,{img_b64}" style="height:54px;width:54px;object-fit:contain;border-radius:8px;background:#fff;">'
    else:
        icon_html = '<div style="width: 54px; height: 54px; background: linear-gradient(135deg, #9c7a32, #c9a84c); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; flex-shrink: 0;">🔬</div>'

    st.markdown(f"""
    <div style="
        display:flex; align-items:center; justify-content:space-between;
        padding: 1.5rem 2rem;
        background: linear-gradient(135deg, #0b1120 0%, #0f1a2e 100%);
        border-radius: 4px;
        margin-bottom: 1.5rem;
        margin-top: 0.5rem;
    ">
        <div style="display:flex;align-items:center;gap:1.5rem;">
            {icon_html}
            <div>
                <div style="
                    font-family:'Playfair Display',Georgia,serif;
                    font-size:1.75rem;
                    font-weight:700;
                    color:#f0f4fb;
                    line-height:1.1;
                ">Tensile Extrapolation Suite <span style="color:#c9a84c;">2.1</span></div>
                <div style="
                    font-family:'IBM Plex Sans',sans-serif;
                    font-size:0.72rem;
                    color:#a8b4c8;
                    letter-spacing:0.2em;
                    text-transform:uppercase;
                    margin-top:4px;
                ">Analytical Framework for Strain Behavior &nbsp;·&nbsp; Solomon Scientific</div>
            </div>
        </div>
        <div style="
            font-family:'IBM Plex Sans',sans-serif;
            font-size:0.65rem;
            color:#64748b;
            letter-spacing:0.12em;
            text-transform:uppercase;
            text-align:right;
            line-height:1.8;
        ">
            © 2026<br>Research Use
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_sidebar_brand():
    logo_path = "LOGO.png"
    img_b64 = get_base64(logo_path)
    if img_b64:
        icon_html = f'<img src="data:image/png;base64,{img_b64}" style="width:52px;height:52px;object-fit:contain;border-radius:8px;background:#fff;margin: 0 auto 0.75rem auto; display: block;">'
    else:
        icon_html = '<div style="width:52px;height:52px;margin:0 auto 0.75rem auto;background:linear-gradient(135deg,#9c7a32,#c9a84c);border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:1.5rem;">🔬</div>'

    st.markdown(f"""
    <div style="padding:1.25rem 0 0.5rem 0;text-align:center;">
        {icon_html}
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:0.65rem;color:#9c7a32;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:4px;font-weight:700;">Solomon Scientific</div>
        <div style="font-family:'Playfair Display',Georgia,serif;font-size:1.1rem;font-weight:700;color:#111827;line-height:1.2;">
            Extrapolation Pro <span style="color:#c9a84c;">2.1</span>
        </div>
        <div style="
            margin-top:0.75rem;padding-top:0.75rem;border-top:1px solid #e2e8f0;
            font-family:'IBM Plex Sans',sans-serif;font-size:0.68rem;color:#64748b;line-height:1.5;
        ">
            Advanced Modeling Tools &nbsp;<br>
            <a href='mailto:your.solomon.duf@gmail.com' style='color:#9c7a32;text-decoration:none;font-weight:500;'>✉ Contact Developer</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

render_header()

# --- 3. Sidebar: Professional Inputs ---
with st.sidebar:
    render_sidebar_brand()
    
    st.markdown("### 📝 Project Metadata")
    project_name = st.text_input("Research Topic", "PBAT-PLA-Biocomposites")

    st.markdown("### 📏 Specimen Geometry")
    thickness = st.number_input("Thickness (mm)", value=4.0, step=0.1)
    width = st.number_input("Width (mm)", value=4.0, step=0.1)
    gauge_length = st.number_input("Initial Gauge Length (L0) [mm]", value=25.0, step=1.0)
    area = width * thickness 

    st.markdown("### ⚙️ Data Calibration")
    unit_input = st.selectbox("Raw Displacement Unit", ["Millimeters (mm)", "Micrometers (um)", "Meters (m)"])
    scale_map = {"Millimeters (mm)": 1.0, "Micrometers (um)": 0.001, "Meters (m)": 1000.0}
    u_scale = scale_map[unit_input]

    apply_zeroing = st.checkbox("Apply Toe-Compensation", value=True)

    st.markdown("### 🎨 Plot Customization")
    line_thickness = st.slider("Line Thickness (Journal Plot)", 0.5, 5.0, 2.0, 0.5)
    legend_pos = st.selectbox("Legend Position", ["lower right", "upper right", "upper left", "lower left", "best", "outside"], index=0)

    auto_scale = st.checkbox("Enable Auto-Scale", value=True)
    if not auto_scale:
        custom_x_max = st.number_input("Manual X Max (Strain %)", value=10.0)
        custom_y_max = st.number_input("Manual Y Max (Stress MPa)", value=50.0)

# --- 20 MAXIMUM CONTRAST COLORS (KELLY'S SET) ---
distinct_20 = [
    "#c9a84c", "#111827", "#e05252", "#3a7bd5", "#3db87a", "#803E75", "#FF6800",
    "#817066", "#007D34", "#F6768E", "#00538A", "#FF7A5C", "#53377A", "#FF8E00",
    "#B32851", "#F4C800", "#7F180D", "#93AA00", "#593315", "#F13A13", "#232C16"
]

def clean_label(name):
    return re.sub(r'\.(txt|csv|xlsx|xls)$', '', name, flags=re.IGNORECASE)

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
                fill_color="rgba(201, 168, 76, 0.3)", 
                stroke_width=2, 
                stroke_color="#e05252",
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
    sample_color_map = {}

    st.sidebar.markdown("### 🎨 Manual Colors")

    st.subheader("🛠️ Sample Configuration & Modulus Validation")
    with st.expander("⚡ Bulk Update (Apply to All Samples)"):
        b1, b2, b3, b4 = st.columns([2, 2, 2, 1])
        bulk_range = b1.slider("Global Modulus Range (%)", 0.0, 20.0, (0.2, 1.0), key="bulk_slider")
        bulk_method = b2.selectbox("Global Yield Method", ["Offset Method", "Departure from Linearity"], key="bulk_method")
        bulk_val = b3.slider("Global Sensitivity/Offset (%)", 0.0, 45.0, 0.2, 0.05, key="bulk_val")
        if b4.button("Apply to All"):
            for file in uploaded_files:
                if file: 
                    st.session_state[f"range_{file.name}"] = bulk_range
                    st.session_state[f"meth_{file.name}"] = bulk_method
                    st.session_state[f"val_{file.name}"] = bulk_val
            st.rerun()

    for idx, file in enumerate(uploaded_files):
        if file is None: continue
        df = smart_load(file)
        if df is None or df.empty: continue
        
        cols = df.columns.tolist()
        inst_stress_col = next((c for c in cols if "sforzo" in c.lower()), None)
        def_f = inst_stress_col if inst_stress_col else (cols[1] if "Digitized Stress" in cols else cols[0])
        def_d = cols[0] if "Digitized Strain" in cols else cols[1]

        f_col = st.sidebar.selectbox(f"Force/Stress ({file.name})", cols, index=cols.index(def_f), key=f"f_{file.name}")
        d_col = st.sidebar.selectbox(f"Disp/Strain ({file.name})", cols, index=cols.index(def_d), key=f"d_{file.name}")
        
        chosen_color = st.sidebar.color_picker(f"Color: {clean_label(file.name)}", value=distinct_20[idx % len(distinct_20)], key=f"color_{file.name}")

        df_clean = df[[f_col, d_col]].apply(pd.to_numeric, errors='coerce').dropna()
        
        if "Digitized" in str(file.name):
            stress_all = df_clean[f_col].values
            strain_all = df_clean[d_col].values
        else:
            disp_all = df_clean[d_col].values * u_scale
            stress_all = df_clean[f_col].values if (inst_stress_col and f_col == inst_stress_col) else (df_clean[f_col].values / area)
            strain_all = (disp_all / gauge_length) * 100

        peak_idx = np.argmax(stress_all)
        stress_raw = stress_all[:peak_idx + 1]
        strain_raw = strain_all[:peak_idx + 1]

        with st.expander(f"Adjust & Preview: {file.name}", expanded=False):
            custom_name = st.text_input("Scientific Display Name", value=clean_label(file.name), key=f"name_{file.name}")
            c1, c2, c3, prev_col = st.columns([1.2, 1.2, 1.2, 3])
            
            sample_color_map[custom_name] = chosen_color

            current_range = c1.slider("Modulus Fit Range (%)", 0.0, 20.0, (0.2, 1.0), key=f"range_{file.name}")
            yield_method = c2.selectbox("Yield Method", ["Offset Method", "Departure from Linearity"], key=f"meth_{file.name}")
            yield_val = c3.slider("Sensitivity/Offset (%)", 0.0, 45.0, 0.2, 0.05, key=f"val_{file.name}")
            
            mask_e = (strain_raw >= current_range[0]) & (strain_raw <= current_range[1])
            
            if np.sum(mask_e) >= 3:
                E_slope, intercept_y = np.polyfit(strain_raw[mask_e], stress_raw[mask_e], 1)
                
                if apply_zeroing:
                    shift = -intercept_y / E_slope
                    strain_plot = strain_raw - shift
                    mask_pos = (strain_plot >= 0)
                    strain_plot, stress_plot = strain_plot[mask_pos], stress_raw[mask_pos]
                    
                    if len(strain_plot) > 0 and strain_plot[0] > 0:
                        strain_plot = np.insert(strain_plot, 0, 0.0)
                        stress_plot = np.insert(stress_plot, 0, 0.0)
                else:
                    strain_plot, stress_plot = strain_raw, stress_raw

                plot_data_storage[custom_name] = (strain_plot, stress_plot)
                fit_x = np.linspace(0, current_range[1] * 2, 20)
                fit_y = E_slope * fit_x + (0 if apply_zeroing else intercept_y)
                modulus_fit_storage[custom_name] = (fit_x, fit_y)

                if yield_method == "Offset Method":
                    offset_line = E_slope * (strain_plot - yield_val)
                    idx_yield = np.where(stress_plot < offset_line)[0]
                else:
                    theoretical_stress = E_slope * strain_plot + (0 if apply_zeroing else intercept_y)
                    deviation = (theoretical_stress - stress_plot) / theoretical_stress
                    idx_yield = np.where(deviation > (yield_val/10))[0]

                if len(idx_yield) > 0:
                    y_stress, y_strain, mat_class = round(stress_plot[idx_yield[0]], 2), round(strain_plot[idx_yield[0]], 2), "Ductile"
                else:
                    y_stress, y_strain, mat_class = "N/A", "N/A", "Brittle"

                fig_mini = go.Figure()
                fig_mini.add_trace(go.Scatter(x=strain_plot, y=stress_plot, name="Data", line=dict(color=chosen_color)))
                fig_mini.add_trace(go.Scatter(x=fit_x, y=fit_y, name="Modulus Fit", line=dict(dash='dot', color='#111827')))
                
                if y_stress != "N/A":
                    fig_mini.add_trace(go.Scatter(x=[y_strain], y=[y_stress], mode='markers', marker=dict(color='#e05252', size=12, symbol='circle-open-dot')))

                fig_mini.update_layout(height=280, margin=dict(l=0, r=0, t=0, b=0), plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', showlegend=False, xaxis=dict(range=[0, None], showgrid=False, linecolor='#e2e8f0'), yaxis=dict(range=[0, None], showgrid=False, linecolor='#e2e8f0'))
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
                c1.error("Insufficient points.")

    # --- 9. Final Reports & Visualizations ---
    if all_results:
        res_df = pd.DataFrame(all_results)
        st.divider()
        view_mode = st.radio("Select Visualization Mode", ["Interactive (Cursor Inspection)", "Static (High-Res Journal TIFF)"], horizontal=True)

        # Construct common Matplotlib plot for High-Res
        plt.rcParams.update({
            "font.family": "serif", "font.serif": ["Times New Roman"], "font.size": 12,
            "axes.linewidth": 1.5, "xtick.direction": "in", "ytick.direction": "in",
            "xtick.major.size": 6, "ytick.major.size": 6, "xtick.top": True, "ytick.right": True
        })
        fig_journal, ax_journal = plt.subplots(figsize=(7, 6), dpi=600)
        for name, data in plot_data_storage.items():
            ax_journal.plot(data[0], data[1], label=name, color=sample_color_map.get(name, '#000000'), lw=line_thickness)
        
        ax_journal.set_xbound(lower=0); ax_journal.set_ybound(lower=0)
        if not auto_scale:
            ax_journal.set_xlim(0, custom_x_max); ax_journal.set_ylim(0, custom_y_max)
        else:
            ax_journal.set_xlim(0, res_df["Strain @ Peak [%]"].max() * 1.05)
            ax_journal.set_ylim(0, res_df["Stress @ Peak [MPa]"].max() * 1.1)
        
        ax_journal.set_xlabel('Strain (%)', fontweight='bold', labelpad=10)
        ax_journal.set_ylabel('Stress (MPa)', fontweight='bold', labelpad=10)
        ax_journal.legend(loc=legend_pos, frameon=False)
        plt.tight_layout()

        if view_mode == "Interactive (Cursor Inspection)":
            fig_main = go.Figure()
            for name, data in plot_data_storage.items():
                fig_main.add_trace(go.Scatter(x=data[0], y=data[1], name=name, mode='lines', 
                                             line=dict(width=line_thickness, color=sample_color_map.get(name, '#000000'))))
            x_lim = res_df["Strain @ Peak [%]"].max() * 1.05 if auto_scale else custom_x_max
            y_lim = res_df["Stress @ Peak [MPa]"].max() * 1.1 if auto_scale else custom_y_max
            fig_main.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', font=dict(color='#111827'), xaxis=dict(title="Strain (%)", range=[0, x_lim], showgrid=False, linecolor='#000000', linewidth=2, ticks='inside'), yaxis=dict(title="Stress (MPa)", range=[0, y_lim], showgrid=False, linecolor='#000000', linewidth=2, ticks='inside'), height=650)
            st.plotly_chart(fig_main, use_container_width=True)
        else:
            st.pyplot(fig_journal)
            
            # --- TIFF Export ---
            img_buf = io.BytesIO()
            fig_journal.savefig(img_buf, format='png', dpi=600, bbox_inches='tight')
            img_buf.seek(0)
            pil_img = Image.open(img_buf)
            tiff_buf = io.BytesIO()
            pil_img.save(tiff_buf, format='TIFF', compression='tiff_lzw', dpi=(600, 600))
            st.download_button("📥 Download 600DPI TIFF (Journal Ready)", data=tiff_buf.getvalue(), file_name="HighRes_Journal_Plot.tiff", mime="image/tiff")

        st.divider()
        st.subheader("⚖️ Batch Property Comparison")
        col_comp1, col_comp2 = st.columns([1, 2])
        control_sample = col_comp1.selectbox("Select Control Sample", res_df["Sample"].tolist())
        comp_df = res_df.copy()
        if control_sample:
            baseline = res_df[res_df["Sample"] == control_sample].iloc[0]
            for col, base in [("Modulus (E) [MPa]", "Modulus (E) [MPa]"), ("Stress @ Peak [MPa]", "Stress @ Peak [MPa]"), ("Toughness [MJ/m³]", "Toughness [MJ/m³]")]:
                comp_df[f"{col.split()[0]} Δ (%)"] = ((pd.to_numeric(comp_df[col], errors='coerce') - float(baseline[base])) / float(baseline[base])) * 100
            st.dataframe(comp_df.style.format("{:+.1f}%", subset=[c for c in comp_df.columns if "Δ" in c]).background_gradient(cmap="Blues", subset=[c for c in comp_df.columns if "Δ" in c]), hide_index=True)

        st.subheader(f"📊 Batch Summary Statistics (n={len(res_df)})")
        numeric_cols = ["Modulus (E) [MPa]", "Yield Stress [MPa]", "Yield Strain [%]", "Stress @ Peak [MPa]", "Strain @ Peak [%]", "Toughness [MJ/m³]"]
        stats_df = res_df[numeric_cols].apply(pd.to_numeric, errors='coerce').agg(['mean', 'std']).T
        st.table(stats_df.style.format("{:.2f}"))

        st.subheader("📋 Complete Individual Test Records")
        st.dataframe(res_df, hide_index=True, use_container_width=True)

        # --- 13. COMPREHENSIVE EXPORT MODULE ---
        st.divider()
        excel_out = io.BytesIO()
        with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
            # 1. Individual Test Records
            res_df.to_excel(writer, sheet_name='Individual_Results', index=False)
            
            # 2. Batch Summary Stats
            stats_df.to_excel(writer, sheet_name='Batch_Statistics')
            
            # 3. Comparison Delta Analysis
            if 'comp_df' in locals():
                comp_df.to_excel(writer, sheet_name='Comparative_Analysis', index=False)
            
            # 4. Final Plot Embedding
            plot_sheet = writer.book.add_worksheet('Final_Visual_Report')
            plot_sheet.write('A1', f'Project: {project_name}')
            plot_sheet.write('A2', 'Note: This image is exported at 600 DPI for publication quality.')
            
            img_excel = io.BytesIO()
            fig_journal.savefig(img_excel, format='png', dpi=300, bbox_inches='tight') # Reduced DPI for Excel to save space
            img_excel.seek(0)
            plot_sheet.insert_image('A4', 'final_plot.png', {'image_data': img_excel, 'x_scale': 0.8, 'y_scale': 0.8})

        st.download_button(
            label="📥 Download Full Research Report (Excel + Plot)",
            data=excel_out.getvalue(),
            file_name=f"{project_name}_Full_Analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
