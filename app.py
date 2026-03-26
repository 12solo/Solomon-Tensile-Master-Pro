import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from scipy.interpolate import interp1d
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research Suite - Batch Analysis", layout="wide")

# Initialize Session State for Multi-Sample Storage
if 'samples' not in st.session_state:
    st.session_state.samples = {}

# --- 2. Professional Header & Logo ---
logo_url = "https://raw.githubusercontent.com/12solo/Tensile-test-extrapolator/main/logo%20s.png"
col_logo, col_text = st.columns([1, 5])
with col_logo:
    try:
        st.image(logo_url, width=150)
    except:
        st.header("🔬")
with col_text:
    st.title("Solomon Tensile Suite: Research Edition")
    st.markdown("**Advanced Statistical Master Curve & Batch Analytics** 🚀")

# --- 3. Sidebar: Global Metadata & QC ---
st.sidebar.header("📂 Research Metadata")
project_name = st.sidebar.text_input("Project Name", "PBAT/PLA Synergy Study")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)
target_def = st.sidebar.number_input("Target Extrapolation (mm)", value=400.0)

st.sidebar.header("✍️ Validation & QC")
verified_by = st.sidebar.text_input("Digital Signature", "Solomon Dufera Tolcha")
qc_status = st.sidebar.selectbox("QC Approval", ["Pending", "Approved", "Requires Re-test"])

if st.sidebar.button("Clear All Data"):
    st.session_state.samples = {}
    st.rerun()

# --- 4. Data Acquisition ---
st.subheader("1. Populate Batch Dataset")
uploaded_file = st.file_uploader("Upload Sample Data (CSV/Excel)", type=['csv', 'xlsx'])

if uploaded_file:
    sample_name = st.text_input("Sample Label (e.g., S1-Control)", uploaded_file.name.split('.')[0])
    df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    cols = df_raw.columns.tolist()
    
    c1, c2 = st.columns(2)
    with c1: f_col = st.selectbox("Force Column (N)", cols, key=f"f_{sample_name}")
    with c2: d_col = st.selectbox("Deformation Column (mm)", cols, key=f"d_{sample_name}")
    
    if st.button(f"Add {sample_name} to Research Batch"):
        # Unit Conversion to Stress/Strain
        stress = df_raw[f_col].values / area
        strain = (df_raw[d_col].values / gauge_length) * 100
        
        # High-Fidelity Extrapolation
        slope, _ = np.polyfit(strain[-30:], stress[-30:], 1)
        target_strain = (target_def / gauge_length) * 100
        strain_ext = np.linspace(strain[-1], target_strain, 100)
        stress_ext = stress[-1] + slope * (strain_ext - strain[-1])
        
        full_strain = np.concatenate([strain, strain_ext[1:]])
        full_stress = np.concatenate([stress, stress_ext[1:]])
        
        st.session_state.samples[sample_name] = {"strain": full_strain, "stress": full_stress}
        st.success(f"Sample '{sample_name}' integrated successfully.")

# --- 5. Statistical Analytics Engine ---
if st.session_state.samples:
    st.divider()
    st.subheader("2. Statistical Master Curve & Comparison")
    
    # Interpolation for Statistical Consistency
    max_grid_strain = (target_def / gauge_length) * 100
    common_strain = np.linspace(0, max_grid_strain, 500)
    all_stresses = []
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot Individual Traces
    for name, data in st.session_state.samples.items():
        f_interp = interp1d(data['strain'], data['stress'], bounds_error=False, fill_value="extrapolate")
        interp_stress = f_interp(common_strain)
        all_stresses.append(interp_stress)
        ax.plot(common_strain, interp_stress, color='grey', alpha=0.25, lw=1)

    # Calculate Mean & Standard Deviation
    master_mean = np.mean(all_stresses, axis=0)
    master_std = np.std(all_stresses, axis=0)
    
    # Plot Master Curve with Confidence Interval
    ax.plot(common_strain, master_mean, color='#1f77b4', label='MASTER CURVE (Mean)', lw=3)
    ax.fill_between(common_strain, master_mean - master_std, master_mean + master_std, color='#1f77b4', alpha=0.15, label='Standard Deviation')
    
    ax.set_xlabel("Strain (%)", fontweight='bold')
    ax.set_ylabel("Stress (MPa)", fontweight='bold')
    ax.set_title(f"Project: {project_name} | Comparative Mechanical Analysis", fontsize=14)
    ax.legend()
    ax.grid(True, alpha=0.2)
    st.pyplot(fig)
    
    # --- 6. Export Branded Research Report ---
    st.subheader("3. Export Formal Documentation")
    
    # 1. Create the Summary DataFrame
    df_master = pd.DataFrame({
        'Strain (%)': common_strain,
        'Mean Stress (MPa)': master_mean,
        'Std Dev (MPa)': master_std
    })

    # 2. Capture the Matplotlib Plot
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=120)
    img_buffer.seek(0)

    # 3. Capture Logo from GitHub (Optional check)
    logo_data = io.BytesIO()
    try:
        r = requests.get(logo_url, timeout=5)
        logo_data.write(r.content)
        logo_data.seek(0)
        has_logo = True
    except:
        has_logo = False

    # 4. Generate the Excel File
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Sheet 1: Master Curve Data
            df_master.to_excel(writer, index=False, sheet_name="Master Curve Data")
            
            workbook = writer.book
            worksheet = workbook.add_worksheet("Validation & Summary")
            writer.sheets["Validation & Summary"] = worksheet
            
            # Formatting
            title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#1f77b4'})
            label_fmt = workbook.add_format({'bold': True})
            
            # Header Info
            worksheet.write('A1', 'RESEARCH VALIDATION REPORT', title_fmt)
            if has_logo:
                worksheet.insert_image('G1', 'logo.png', {'image_data': logo_data, 'x_scale': 0.3, 'y_scale': 0.3})
            
            worksheet.write('A3', 'Project Name:', label_fmt)
            worksheet.write('B3', project_name)
            worksheet.write('A4', 'Verified By:', label_fmt)
            worksheet.write('B4', verified_by)
            worksheet.write('A5', 'QC Status:', label_fmt)
            worksheet.write('B5', qc_status)
            worksheet.write('A6', 'Timestamp:', label_fmt)
            worksheet.write('B6', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Insert Comparative Graph
            worksheet.insert_image('A8', 'master_plot.png', {'image_data': img_buffer, 'x_scale': 0.7, 'y_scale': 0.7})
            
            # Add individual sheets for each sample in the batch
            for name, data in st.session_state.samples.items():
                sample_df = pd.DataFrame({'Strain (%)': data['strain'], 'Stress (MPa)': data['stress']})
                # Excel sheet names must be <= 31 characters
                clean_name = "".join([c for c in name if c.isalnum() or c in (' ', '_')])[:30]
                sample_df.to_excel(writer, sheet_name=clean_name, index=False)
                
        # 5. The Download Button
        st.download_button(
            label=f"📥 Download Research Report ({len(st.session_state.samples)} Samples)", 
            data=output.getvalue(), 
            file_name=f"Research_Report_{project_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Excel Export Error: {e}")
