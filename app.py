import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy import stats
from datetime import datetime

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research - Batch Characterization", layout="wide")

if 'experimental_batch' not in st.session_state: 
    st.session_state.experimental_batch = {}

# --- 2. Header ---
st.title("Solomon Tensile Suite: Research Edition v2.6")
st.markdown("**Experimental Batch Characterization & Reproducibility Analysis** 🚀")

# --- 3. Sidebar: Global Parameters ---
st.sidebar.header("📂 Sample Dimensions")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("⚙️ Precision Settings")
normalize = st.sidebar.checkbox("Toe-Region Correction", value=True)
search_limit = st.sidebar.slider("Modulus Search Limit (Strain %)", 0.5, 5.0, 2.0)

if st.sidebar.button("🗑️ Clear Batch Data"):
    st.session_state.experimental_batch = {}
    st.rerun()

# --- 4. Bulk Data Acquisition ---
st.subheader("1. Bulk Upload Experimental Samples")
uploaded_files = st.file_uploader("Upload Samples (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"Process {len(uploaded_files)} Experimental Samples"):
        for uploaded_file in uploaded_files:
            sample_label = uploaded_file.name.split('.')[0]
            
            try:
                df_raw = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                f_raw = df_raw.iloc[:, 0].values 
                d_raw = df_raw.iloc[:, 1].values 
            except Exception as e:
                st.error(f"Error reading {uploaded_file.name}: {e}")
                continue

            # 1. Normalization (Zeroing)
            if normalize:
                start_mask = f_raw > 0.1
                idx = np.where(start_mask)[0][0] if any(start_mask) else 0
                f_p, d_p = f_raw[idx:] - f_raw[idx], d_raw[idx:] - d_raw[idx]
            else:
                f_p, d_p = f_raw, d_raw

            stress = f_p / area
            strain = (d_p / gauge_length) * 100 

            # 2. Rolling Modulus (Max Slope)
            mask_e = (strain > 0) & (strain <= search_limit)
            stress_e, strain_e = stress[mask_e], strain[mask_e] / 100 
            
            E_final = 0
            if len(stress_e) > 10:
                window = max(5, int(len(stress_e) * 0.2))
                slopes = [stats.linregress(strain_e[i:i+window], stress_e[i:i+window])[0] for i in range(len(stress_e) - window)]
                E_final = max(slopes) if slopes else 0

            # 3. Yield & Energy
            y_stress = stress[strain <= 25.0].max() if any(strain <= 25.0) else stress.max()
            try:
                work_j = np.trapezoid(f_p, d_p) / 1000.0
            except AttributeError:
                work_j = np.trapz(f_p, d_p) / 1000.0

            st.session_state.experimental_batch[sample_label] = {
                "E (MPa)": round(E_final, 2), 
                "Yield (MPa)": round(y_stress, 2),
                "Break (MPa)": round(stress[-1], 2), 
                "Elongation (%)": round(strain[-1], 2),
                "Work (J)": round(work_j, 4), 
                "Raw_Strain": strain, 
                "Raw_Stress": stress
            }
        st.success("Batch processing complete.")

# --- 5. Statistical Characterization ---
if st.session_state.experimental_batch:
    st.divider()
    # Prepare DataFrame
    df_metrics = pd.DataFrame({k: {m: v for m, v in val.items() if "Raw" not in m} for k, val in st.session_state.experimental_batch.items()}).T
    
    # Calculate Batch Stats
    stats_summary = pd.DataFrame({
        "Mean": df_metrics.mean(),
        "Std Dev": df_metrics.std(),
        "RSD (%)": (df_metrics.std() / df_metrics.mean()) * 100
    }).T

    st.subheader("2. Batch Statistical Summary")
    col_t, col_s = st.columns([2, 1])
    with col_t:
        st.markdown("**Individual Sample Metrics**")
        st.dataframe(df_metrics, use_container_width=True)
    with col_s:
        st.markdown("**Reproducibility Analysis**")
        st.dataframe(stats_summary.style.format(precision=2), use_container_width=True)

    # Visualization: Overlay and Distribution
    st.subheader("3. Visual Characterization")
    c1, c2 = st.columns(2)
    with c1:
        fig_curve, ax_curve = plt.subplots()
        for label, d in st.session_state.experimental_batch.items():
            ax_curve.plot(d['Raw_Strain'], d['Raw_Stress'], alpha=0.5, label=label)
        ax_curve.set_xlabel("Strain (%)"); ax_curve.set_ylabel("Stress (MPa)"); ax_curve.set_title("Experimental Overlay")
        st.pyplot(fig_curve)
    
    with c2:
        fig_box, ax_box = plt.subplots()
        ax_box.boxplot([df_metrics["E (MPa)"], df_metrics["Yield (MPa)"]], labels=["E (MPa)", "Yield"])
        ax_box.set_title("Property Variance (Internal Consistency)")
        st.pyplot(fig_box)

    # Export
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_metrics.to_excel(writer, sheet_name="All Samples")
        stats_summary.to_excel(writer, sheet_name="Batch Statistics")
    st.download_button("📥 Download Characterization Report", output.getvalue(), "Experimental_Characterization.xlsx")
