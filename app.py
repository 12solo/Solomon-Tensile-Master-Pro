import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
from scipy import stats

# --- 1. Page Configuration ---
st.set_page_config(page_title="Solomon Research - Individual Metrics", layout="wide")

if 'experimental_batch' not in st.session_state: 
    st.session_state.experimental_batch = {}

# --- 2. Header ---
st.title("Solomon Tensile Suite: Research Edition v2.6.1")
st.markdown("**Individual Sample Characterization & Precision Modulus Extraction** 🚀")

# --- 3. Sidebar Setup ---
st.sidebar.header("📂 Specimen Dimensions")
area = st.sidebar.number_input("Cross-sectional Area (mm²)", value=16.0)
gauge_length = st.sidebar.number_input("Initial Gauge Length (mm)", value=50.0)

st.sidebar.header("⚙️ Precision Settings")
normalize = st.sidebar.checkbox("Toe-Region Correction", value=True)
# Search limit is the strain range (e.g., 0% to 2%) where we look for the steepest slope
search_limit = st.sidebar.slider("Modulus Search Limit (Strain %)", 0.5, 5.0, 2.0)

if st.sidebar.button("🗑️ Clear Batch Data"):
    st.session_state.experimental_batch = {}
    st.rerun()

# --- 4. Bulk Processing Loop ---
st.subheader("1. Upload & Calculate Individual Samples")
uploaded_files = st.file_uploader("Upload Samples (CSV/Excel)", type=['csv', 'xlsx'], accept_multiple_files=True)

if uploaded_files:
    if st.button(f"Calculate Metrics for {len(uploaded_files)} Samples"):
        for uploaded_file in uploaded_files:
            name = uploaded_file.name.split('.')[0]
            
            try:
                df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                f_raw, d_raw = df.iloc[:, 0].values, df.iloc[:, 1].values 
            except: continue

            # A. Normalize (Zeroing the curve)
            if normalize:
                idx = np.where(f_raw > 0.1)[0][0] if any(f_raw > 0.1) else 0
                f, d = f_raw[idx:] - f_raw[idx], d_raw[idx:] - d_raw[idx]
            else:
                f, d = f_raw, d_raw

            stress, strain = f / area, (d / gauge_length) * 100 

            # B. INDIVIDUAL MODULUS CALCULATION (E)
            # We use a sliding window to find the MAX slope in the elastic region
            mask_e = (strain > 0) & (strain <= search_limit)
            stress_e, strain_e = stress[mask_e], strain[mask_e] / 100 # mm/mm
            
            e_val = 0
            if len(stress_e) > 10:
                window = max(5, int(len(stress_e) * 0.2))
                # Calculate slope for every window and pick the maximum (stiffest part)
                slopes = [stats.linregress(strain_e[i:i+window], stress_e[i:i+window])[0] for i in range(len(stress_e) - window)]
                e_val = max(slopes) if slopes else 0

            # C. OTHER METRICS
            yield_val = stress[strain <= 25.0].max() if any(strain <= 25.0) else stress.max()
            try: work_val = np.trapezoid(f, d) / 1000.0
            except: work_val = np.trapz(f, d) / 1000.0

            # D. Store results explicitly
            st.session_state.experimental_batch[name] = {
                "E (MPa)": round(e_val, 2),
                "Yield (MPa)": round(yield_val, 2),
                "UTS (MPa)": round(stress.max(), 2),
                "Elongation (%)": round(strain[-1], 2),
                "Work (J)": round(work_val, 4),
                "strain_plot": strain,
                "stress_plot": stress
            }
        st.success("All individual samples processed!")

# --- 5. Results Display ---
if st.session_state.experimental_batch:
    st.divider()
    
    # Create the Results Table
    # This specifically pulls the E (MPa) and other metrics for each sample key
    results_df = pd.DataFrame.from_dict(
        {k: {m: v for m, v in val.items() if "_plot" not in m} for k, val in st.session_state.experimental_batch.items()},
        orient='index'
    )
    results_df.index.name = "Sample ID"

    st.subheader("2. Individual Sample Mechanical Properties")
    st.dataframe(results_df, use_container_width=True)

    # Statistical Summary (Mean/Std/RSD)
    st.markdown("**Batch Statistical Summary**")
    stats_df = pd.DataFrame({
        "Average": results_df.mean(),
        "Std Dev": results_df.std(),
        "RSD (%)": (results_df.std() / results_df.mean()) * 100
    }).T
    st.dataframe(stats_df.style.format(precision=2), use_container_width=True)

    # Visual Overlay
    fig, ax = plt.subplots(figsize=(10, 5))
    for name, data in st.session_state.experimental_batch.items():
        ax.plot(data["strain_plot"], data["stress_plot"], label=name, alpha=0.6)
    ax.set_xlabel("Strain (%)"); ax.set_ylabel("Stress (MPa)")
    ax.set_title("Experimental Overlay - Comparative Stress-Strain")
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    st.pyplot(fig)
