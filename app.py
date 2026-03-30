# --- 10. Batch Comparison (FIXED KEYERROR) ---
        st.divider()
        st.subheader("⚖️ Batch Property Comparison")
        col_comp1, col_comp2 = st.columns([1, 2])
        control_sample = col_comp1.selectbox("Select Control Sample (Baseline)", res_df["Sample"].tolist())
        
        if control_sample:
            baseline = res_df[res_df["Sample"] == control_sample].iloc[0]
            comp_df = res_df.copy()
            
            # Map the exact keys to match the display list below
            comp_df["Modulus Δ (%)"] = pd.to_numeric(comp_df["Modulus (E) [MPa]"], errors='coerce')
            b_mod = pd.to_numeric(baseline["Modulus (E) [MPa]"], errors='coerce')
            comp_df["Modulus Δ (%)"] = ((comp_df["Modulus Δ (%)"] - b_mod) / b_mod) * 100

            comp_df["Strength Δ (%)"] = pd.to_numeric(comp_df["Stress @ Peak [MPa]"], errors='coerce')
            b_str = pd.to_numeric(baseline["Stress @ Peak [MPa]"], errors='coerce')
            comp_df["Strength Δ (%)"] = ((comp_df["Strength Δ (%)"] - b_str) / b_str) * 100

            comp_df["Toughness Δ (%)"] = pd.to_numeric(comp_df["Toughness [MJ/m³]"], errors='coerce')
            b_tgh = pd.to_numeric(baseline["Toughness [MJ/m³]"], errors='coerce')
            comp_df["Toughness Δ (%)"] = ((comp_df["Toughness Δ (%)"] - b_tgh) / b_tgh) * 100
            
            delta_cols = ["Modulus Δ (%)", "Strength Δ (%)", "Toughness Δ (%)"]
            display_cols = ["Sample", "Class", "Modulus (E) [MPa]", "Modulus Δ (%)", "Stress @ Peak [MPa]", "Strength Δ (%)", "Toughness [MJ/m³]", "Toughness Δ (%)"]
            
            st.dataframe(
                comp_df[display_cols].style.format("{:+.1f}%", subset=delta_cols)
                .background_gradient(subset=delta_cols, cmap="RdYlGn"),
                hide_index=True, use_container_width=True
            )
