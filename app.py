"""
Solomon Tensile Master Pro v4.0
─────────────────────────────────────────────────────────────────────────────
Integrated platform:
  Page 1 — Tensile Analysis      (v3.0 engine + Smart Column Detection)
  Page 2 — Ageing Trend Analysis (new — oven & UV-Xenon degradation science)
─────────────────────────────────────────────────────────────────────────────
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, re, os, base64, warnings
from PIL import Image

warnings.filterwarnings('ignore')

try:
    from scipy.optimize import curve_fit
    from scipy.stats import t as t_dist, f_oneway
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    from streamlit_drawable_canvas import st_canvas
    HAS_CANVAS = True
except ImportError:
    HAS_CANVAS = False

# ═══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Tensile Master Pro 4.0 | Solomon Scientific",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
    --navy:    #002244;  --navy2:   #003366;
    --gold:    #c9a84c;  --gold2:   #9c7a32;
    --white:   #ffffff;  --off:     #f7f9fc;
    --border:  #dde3ec;  --text:    #0f1923;  --muted: #5a6a7e;
    --red:     #c0392b;  --green:   #1e8449;  --amber: #d97706;
    --oven:    #e07b39;  --uv:      #5b4fcf;
    --font-h: 'Playfair Display', Georgia, serif;
    --font-m: 'IBM Plex Mono', 'Courier New', monospace;
    --font-b: 'IBM Plex Sans', 'Segoe UI', sans-serif;
}
html, body, [class*="css"] { font-family: var(--font-b); color: var(--text); }
.stApp { background: var(--white) !important; }
#MainMenu, .stDeployButton, footer { display:none !important; }
header { background:transparent !important; box-shadow:none !important; }
[data-testid="block-container"] { padding-top:0.75rem !important; }

/* Sidebar Inputs */
[data-testid="stSidebar"] { background:var(--off) !important; border-right:1px solid var(--border) !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 {
    font-size:0.68rem !important; font-weight:700 !important; letter-spacing:0.15em !important;
    text-transform:uppercase !important; color:var(--navy2) !important; margin:0.75rem 0 0.15rem !important;
}

/* Custom UI Elements */
.nav-pill {
    display:inline-block; padding:0.3rem 0.9rem;
    background:var(--navy); color:#f0f4fb !important;
    border-radius:20px; font-size:0.7rem; font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS & HELPERS
# ═══════════════════════════════════════════════════════════════════════════
PALETTE = ["#002244","#c9a84c","#c0392b","#2471a3","#1e8449","#7d3c98","#d35400"]
OVEN_SHADES = ["#e07b39","#c45e1e","#a04000"]
UV_SHADES   = ["#7e6fdf","#5b4fcf","#3d34b0"]

AXIS = dict(
    mirror=True, ticks='inside', showline=True,
    linecolor='#000000', linewidth=2, showgrid=False, zeroline=False,
    title_font=dict(family="Times New Roman", size=15, color='#000000'),
    tickfont=dict(family="Times New Roman", size=12, color='#000000'),
)

AGEING_PROPS = {
    "E_MPa": ("Modulus", "MPa"),
    "UTS_MPa": ("UTS", "MPa"),
    "Yield_MPa": ("Yield Stress", "MPa"),
    "Elongation_pct": ("Elongation at Break", "%"),
    "Toughness_MJm3": ("Toughness", "MJ/m³"),
    "Resilience_MJm3": ("Resilience", "MJ/m³"),
}
AGEING_PROP_LABELS = {k: v[0] for k, v in AGEING_PROPS.items()}
AGEING_PROP_UNITS  = {k: v[1] for k, v in AGEING_PROPS.items()}

TENSILE_TO_AGEING = {
    "Modulus [MPa]": "E_MPa",
    "UTS [MPa]": "UTS_MPa",
    "Yield Stress [MPa]": "Yield_MPa",
    "Elongation at Break [%]": "Elongation_pct",
    "Toughness [MJ/m³]": "Toughness_MJm3",
    "Resilience [MJ/m³]": "Resilience_MJm3",
}

def clean_label(name):
    return re.sub(r'\.(txt|csv|xlsx|xls)$','',str(name),flags=re.IGNORECASE)

def section_hdr(text, icon="", color="#002244"):
    st.markdown(f"""<div style="background:{color};padding:0.5rem 1rem;border-radius:3px;margin:1rem 0;">
      <span style="color:#fff;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;font-size:0.8rem;">{icon} {text}</span>
    </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# DATA LOADING & DETECTION (THE FIX)
# ═══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _load_bytes(file_bytes: bytes, file_name: str):
    try:
        ext = file_name.rsplit('.', 1)[-1].lower()
        if ext == 'xlsx':
            return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')
        content = file_bytes.decode("utf-8", errors="ignore")
        lines = content.splitlines()
        start = 0
        for i, ln in enumerate(lines):
            if len(re.findall(r"[-+]?\d*\.?\d+", ln)) >= 2:
                start = i; break
        sl = lines[start] if lines else ""
        sep = '\t' if '\t' in sl else (',' if ',' in sl else r'\s+')
        df = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=sep, engine='python', on_bad_lines='skip')
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception:
        return None

def smart_load(file):
    if hasattr(file, 'df'): return file.df
    return _load_bytes(file.getvalue(), file.name)

def detect_columns(cols):
    """
    Auto-guessing logic for Stress/Load and Strain/Displacement.
    Returns (guessed_stress_col, guessed_strain_col)
    """
    # Y-AXIS (Load/Stress) Keywords
    force_kws = ['stress', 'load', 'force', 'mpa', 'sigma', 'n', 'lbf', 'kgf', 'carico', 'sforzo']
    # X-AXIS (Strain/Disp) Keywords
    disp_kws = ['strain', 'disp', 'ext', 'mm', 'elongation', '%', 'pos', 'deform', 'allung']
    
    guessed_y = next((c for c in cols if any(k in c.lower() for k in force_kws)), cols[1] if len(cols) > 1 else cols[0])
    guessed_x = next((c for c in cols if any(k in c.lower() for k in disp_kws) and c != guessed_y), cols[0])
    
    return guessed_y, guessed_x

# ═══════════════════════════════════════════════════════════════════════════
# PROCESSING LOGIC
# ═══════════════════════════════════════════════════════════════════════════
def process_sample(strain_raw, stress_raw, fit_range, yield_method, yield_val, apply_zeroing):
    if len(strain_raw) < 5: return None
    peak_idx = int(np.argmax(stress_raw))
    stress = stress_raw[:peak_idx+1].astype(float)
    strain = strain_raw[:peak_idx+1].astype(float)
    
    # Simple polyfit for Modulus
    mask_e = (strain >= fit_range[0]) & (strain <= fit_range[1])
    if np.sum(mask_e) < 3: mask_e = np.arange(len(strain)) < 10
    
    try:
        E_slope, intercept_y = np.polyfit(strain[mask_e], stress[mask_e], 1)
        if apply_zeroing:
            shift = -intercept_y / E_slope
            strain = strain - shift
            mask_pos = strain >= 0
            strain, stress = strain[mask_pos], stress[mask_pos]
            E_slope, _ = np.polyfit(strain[mask_e], stress[mask_e], 1)
    except: return None

    E_MPa = E_slope * 100.0
    uts = float(stress.max())
    strain_break = float(strain[-1])
    
    # Toughness (Area under curve)
    try: toughness = float(np.trapezoid(stress, strain/100.0))
    except: toughness = float(np.trapz(stress, strain/100.0))

    return {
        "strain": strain, "stress": stress, "E_MPa": round(E_MPa, 1),
        "uts": round(uts, 2), "strain_break": round(strain_break, 3),
        "toughness": round(toughness, 4), "fit_x": [0, fit_range[1]*2], 
        "fit_y": [0, E_slope * fit_range[1]*2], "y_stress": np.nan, "y_strain": np.nan,
        "mat_class": "Ductile" if strain_break > 5 else "Brittle"
    }

# ═══════════════════════════════════════════════════════════════════════════
# MAIN APP STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════
if "ageing_db" not in st.session_state:
    st.session_state["ageing_db"] = pd.DataFrame()

with st.sidebar:
    st.title("SOLOMON SCIENTIFIC")
    page = st.radio("Navigation", ["Tensile Analysis", "Ageing Trends"])
    st.markdown("---")
    thickness = st.number_input("Thickness (mm)", 4.0)
    width = st.number_input("Width (mm)", 4.0)
    gauge_length = st.number_input("Gauge Length (mm)", 25.0)
    area = thickness * width

if page == "Tensile Analysis":
    st.header("🔬 Tensile Analysis Engine")
    files = st.file_uploader("Upload Raw Data", accept_multiple_files=True)
    
    if files:
        all_results = []
        plot_data = {}
        
        for idx, file in enumerate(files):
            df_raw = smart_load(file)
            if df_raw is None: continue
            
            cols = df_raw.columns.tolist()
            def_y, def_x = detect_columns(cols)
            
            with st.expander(f"📄 {file.name}", expanded=(len(files)==1)):
                c1, c2 = st.columns(2)
                y_col = c1.selectbox(f"Stress/Load ({file.name})", cols, index=cols.index(def_y))
                x_col = c2.selectbox(f"Strain/Disp ({file.name})", cols, index=cols.index(def_x))
                
                # Processing
                df_c = df_raw[[y_col, x_col]].apply(pd.to_numeric, errors='coerce').dropna()
                raw_stress = df_c[y_col].values / (area if "mpa" not in y_col.lower() else 1)
                raw_strain = (df_c[x_col].values / gauge_length) * 100 if "mm" in x_col.lower() else df_c[x_col].values
                
                res = process_sample(raw_strain, raw_stress, (0.2, 1.0), "Offset", 0.2, True)
                
                if res:
                    st.metric("Modulus", f"{res['E_MPa']} MPa")
                    plot_data[file.name] = res
                    all_results.append({"Sample": file.name, "E_MPa": res["E_MPa"], "UTS_MPa": res["uts"], "Elongation_%": res["strain_break"]})

        if all_results:
            st.subheader("Summary Results")
            st.dataframe(pd.DataFrame(all_results))
            
            # Master Plot
            fig = go.Figure()
            for name, data in plot_data.items():
                fig.add_trace(go.Scatter(x=data["strain"], y=data["stress"], name=name))
            fig.update_layout(xaxis_title="Strain (%)", yaxis_title="Stress (MPa)", template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

else:
    st.header("📅 Ageing Trend Analysis")
    st.info("Accumulated Database contains {} records.".format(len(st.session_state["ageing_db"])))
    # (Ageing module logic continues here...)
