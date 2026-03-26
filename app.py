import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy import stats

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research - Calculation Fix", layout="wide")

if 'experimental_batch' not in st.session_state: 
    st.session_state.experimental_batch = {}

# --- 2. Header ---
st.title("Solomon Tensile Suite: Research Edition v2.6.2")
st.markdown("**Corrected Precision Analytics for High-Elongation Bioplastics** 🚀")

# --- 3. Sidebar Setup ---
st.sidebar.header("📂 Specimen Dimensions")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("⚙️ Precision Settings")
normalize = st.sidebar.checkbox("Toe-Region Correction", value=True)
# If your data is low-res, increase this limit to capture more points
search_limit = st.sidebar.slider("Modulus Search Limit (Strain %)", 0.1, 10.0, 2.0)

if st.sidebar.button("🗑️ Clear Batch Data"):
    st.session_state.experimental_batch = {}
    st.rerun()

# --- 4. Bulk Processing Loop ---
st.subheader("1. Process Samples")
uploaded_files = st.file_uploader("Upload Samples", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"Analyze {len(uploaded_files)} Samples"):
        for uploaded_file in uploaded_files:
            name = uploaded_file.name.split('.')[0]
            
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                # Force is assumed to be Column 0, Deformation is Column 1
                f_raw, d_raw = df.iloc[:, 0].values, df.iloc[:, 1].values 
            except: continue

            # A. Toe-Region / Slack Normalization
            if normalize:
                # Find the first index where force is strictly increasing and > 0.01N
                # This is much more sensitive for bioplastics
                start_points = np.where(f_raw > 0.01)[0]
                idx = start_points[0] if len(start_points) > 0 else 0
                f, d = f_raw[idx:] - f_raw[idx], d_raw[idx:] - d_raw[idx]
            else:
                f, d = f_raw, d_raw

            stress = f / area
            strain = (d / gauge_length) * 100 

            # B. MODULUS CALCULATION (E) - REVISED
            # 1. Filter data within the search limit
            mask_e = (strain > 0) & (strain <= search_limit)
            stress_e = stress[mask_e]
            strain_e = strain[mask_e] / 100 # Convert % to mm/mm for MPa slope
            
            e_val = 0
            # Reduced requirement to 5 points to prevent "Zero" results on small files
            if len(stress_e) > 5:
                # Use a smaller window (10% of available elastic data)
                window = max(3, int(len(stress_e) * 0.1))
                slopes = []
                for i in range(len(stress_e) - window):
                    # Linear regression on the sliding window
                    res = stats.linregress(strain_e[i:i+window], stress_e[i:i+window])
                    slopes.append(res.slope)
                
                # Pick the maximum slope found in the elastic region
                e_val = max(slopes) if len(slopes) > 0 else 0

            # C. YIELD & ENERGY
            yield_val = stress[strain <= 25.0].max() if any(strain <= 25.0) else stress.max()
            
            # Numeric integration using the most compatible method
            try: work_val = np.trapezoid(f, d) / 1000.0
            except: work_val = np.trapz(f, d) / 1000.0

            st.session_state.experimental_batch[name] = {
                "E (MPa)": round(e_val, 2),
                "Yield (MPa)": round(yield_val, 2),
                "UTS (MPa)": round(stress.max(), 2),
                "Elongation (%)": round(strain[-1], 2),
                "Work (J)": round(work_val, 4),
                "strain_plot": strain,
                "stress_plot": stress
            }
        st.success("Processing complete. Check results below.")

# --- 5. Results Display ---
if st.session_state.experimental_batch:
    st.divider()
    
    results_df = pd.DataFrame.from_dict(
        {k: {m: v for m, v in val.items() if "_plot" not in m} for k, val in st.session_state.experimental_batch.items()},
        orient='index'
    )
    
    st.subheader("2. Summary Table")
    st.dataframe(results_df, use_container_width=True)

    # Batch Stats
    st.markdown("**Statistical Overview**")
    stats_df = pd.DataFrame({
        "Mean": results_df.mean(),
        "Std Dev": results_df.std(),
        "RSD (%)": (results_df.std() / results_df.mean()) * 100
    }).T
    st.dataframe(stats_df.style.format(precision=2), use_container_width=True)

    # Plots
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, data in st.session_state.experimental_batch.items():
        ax.plot(data["strain_plot"], data["stress_plot"], label=name)
    ax.set_xlabel("Strain (%)"); ax.set_ylabel("Stress (MPa)")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    st.pyplot(fig)
