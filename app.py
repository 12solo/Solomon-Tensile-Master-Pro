import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import io

# --- 1. Page Config ---
st.set_page_config(page_title="Solomon Tensile Suite Pro", layout="wide")

st.title("Solomon Tensile Suite v2.1")
st.markdown("### 🔬 Multi-Format Batch Analysis (CSV, XLSX, TXT)")

# --- 2. Sidebar Geometry & Settings ---
st.sidebar.header("📏 Specimen Geometry")
thickness = st.sidebar.number_input("Thickness (mm)", value=2.0, step=0.1)
width = st.sidebar.number_input("Width (mm)", value=6.0, step=0.1)
gauge_length = st.sidebar.number_input("Gauge Length (mm)", value=25.0, step=1.0)
area = width * thickness 

st.sidebar.header("⚙️ Analysis Parameters")
target_def = st.sidebar.number_input("Extrapolate to (mm)", value=400.0)
ym_start = st.sidebar.slider("Modulus Start Strain (%)", 0.0, 2.0, 0.2)
ym_end = st.sidebar.slider("Modulus End Strain (%)", 0.5, 5.0, 1.0)

# --- 3. File Processing Function ---
def load_data(file):
    """Handles CSV, Excel, and TXT with different separators."""
    ext = file.name.split('.')[-1].lower()
    try:
        if ext == 'csv':
            return pd.read_csv(file)
        elif ext in ['xlsx', 'xls']:
            return pd.read_excel(file)
        elif ext == 'txt':
            # Try Tab separated first, then comma
            content = file.getvalue().decode("utf-8")
            sep = '\t' if '\t' in content else ','
            # Skip rows until we find numeric data (common in lab exports)
            return pd.read_csv(io.StringIO(content), sep=sep, skipinitialspace=True, on_bad_lines='skip')
    except Exception as e:
        st.error(f"Error reading {file.name}: {e}")
        return None

# --- 4. Main App Logic ---
uploaded_files = st.file_uploader("Upload Samples", type=['csv', 'xlsx', 'txt'], accept_multiple_files=True)

if uploaded_files:
    all_results = []
    fig = go.Figure()

    for file in uploaded_files:
        df = load_data(file)
        if df is None or df.empty: continue
        
        # Mapping: Force (1st col), Displacement (2nd col)
        f_col, d_col = df.columns[0], df.columns[1]
        
        # Cleanup: Remove non-numeric rows if they exist
        df[f_col] = pd.to_numeric(df[f_col], errors='coerce')
        df[d_col] = pd.to_numeric(df[d_col], errors='coerce')
        df = df.dropna(subset=[f_col, d_col])

        # --- Extrapolation Logic ---
        slope, intercept = np.polyfit(df[d_col].tail(30), df[f_col].tail(30), 1)
        if df[d_col].iloc[-1] < target_def:
            d_ext = np.linspace(df[d_col].iloc[-1], target_def, 50)
            f_ext = df[f_col].iloc[-1] + slope * (d_ext - df[d_col].iloc[-1])
            df_ext = pd.DataFrame({f_col: f_ext, d_col: d_ext})
            df_full = pd.concat([df[[f_col, d_col]], df_ext], ignore_index=True)
        else:
            df_full = df

      # --- Research Calculations ---
# Calculate energy using the trapezoidal rule (handles NumPy 1.x and 2.x)
try:
    energy_j = np.trapezoid(df_full[f_col], df_full[d_col] / 1000)
except AttributeError:
    energy_j = np.trapz(df_full[f_col], df_full[d_col] / 1000)
        
        # Young's Modulus (E)
        mask_e = (df_full['Strain (%)'] >= ym_start) & (df_full['Strain (%)'] <= ym_end)
        E, _ = np.polyfit(df_full.loc[mask_e, 'Strain (%)'] / 100, df_full.loc[mask_e, 'Stress (MPa)'], 1)
        
        # Toughness (Energy per unit volume)
        energy_j = np.trapz(df_full[f_col], df_full[d_col] / 1000)
        volume_m3 = (area * gauge_length) * 1e-9
        toughness = (energy_j / volume_m3) / 1e6 # MJ/m^3

        # Store results
        all_results.append({
            "Sample": file.name,
            "Modulus (MPa)": E,
            "UTS (MPa)": df_full['Stress (MPa)'].max(),
            "Elongation (%)": df_full['Strain (%)'].iloc[-1],
            "Toughness (MJ/m³)": toughness
        })

        # Add to interactive plot
        fig.add_trace(go.Scatter(x=df_full['Strain (%)'], y=df_full['Stress (MPa)'], name=file.name))

    # --- 5. Visualizations & Stats ---
    st.plotly_chart(fig, use_container_width=True)
    
    res_df = pd.DataFrame(all_results)
    
    # Statistical Table
    st.subheader("📊 Batch Statistics")
    if not res_df.empty:
        summary_stats = res_df.drop(columns='Sample').agg(['mean', 'std']).T
        st.dataframe(summary_stats.style.format("{:.2f}"))

        st.subheader("📋 Individual Results")
        st.dataframe(res_df.style.format(subset=["Modulus (MPa)", "UTS (MPa)", "Elongation (%)", "Toughness (MJ/m³)"], formatter="{:.2f}"))

        # --- 6. Export ---
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            res_df.to_excel(writer, sheet_name='Summary', index=False)
            summary_stats.to_excel(writer, sheet_name='Statistics')
        
        st.download_button(
            label="📥 Download Research Report (Excel)",
            data=output.getvalue(),
            file_name=f"Tensile_Analysis_{project_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Upload files to see analysis. Supported: .csv, .xlsx, .txt (Tab or Comma separated)")
