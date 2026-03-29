# Solomon Tensile Suite 2 🚀
### **Analytical Framework for Bio-Composite Strain Behavior**

The **Solomon Tensile Suite 2** is a high-fidelity mechanical characterization tool built for Material Scientists and Engineers. While optimized for biodegradable polymers—specifically **PBAT and PBAT/PLA blends**—it provides a robust solution for batch-processing raw tensile data, automatic peak detection, and elastic region validation.

## ✨ Key Features

* **Multi-Source Ingestion:** Supports standard Excel (`.xlsx`), CSV, and TXT (instrument raw data from LR 10K and similar) files.
* **Integrated Plot Digitizer:** Extract data directly from legacy plot images or scientific papers using an interactive canvas.
* **Automatic Peak Detection:** Curves are automatically limited to the point of **Maximum Stress (UTS)** to ensure accurate characterization of the material's strength.
* **Interactive Modulus Validation:** Real-time "Modulus Fit" sliders with visual feedback to ensure the elastic slope matches instrument standards.
* **Toe-Region Compensation:** Mathematical shift to $0,0$ to remove initial slack from the mechanical grips.
* **Batch Analytics:** Process multiple samples simultaneously with automated Mean, Standard Deviation, and Specimen Count ($n$) reporting.

---

## 🛠️ Technical Framework

The suite calculates constitutive parameters based on standard engineering mechanics:

1.  **Engineering Stress ($\sigma$):** Calculated as $\sigma = \frac{F}{A_0}$. The app automatically scans for instrument-calculated "Sforzo" (Stress) columns to prioritize raw machine accuracy.
2.  **Engineering Strain ($\epsilon$):** Derived from $\epsilon = \frac{\Delta L}{L_0} \times 100$, where $L_0$ is the user-defined initial gauge length.
3.  **Young’s Modulus ($E$):** Determined via linear regression ($\sigma = E\epsilon + b$) within the user-adjustable elastic range.
4.  **Work Done & Toughness:** Calculated using trapezoidal integration of the area under the stress-strain curve.

---

## 🚀 Getting Started

### Installation
1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/solomon-tensile-suite.git](https://github.com/your-username/solomon-tensile-suite.git)
    cd solomon-tensile-suite
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

## 📖 User Guide

### 1. Specimen Configuration
Set your **Thickness**, **Width**, and **Gauge Length** in the sidebar. These values are critical for converting Force-Displacement into Stress-Strain.

### 2. Upload & Mapping
Upload your files. If using instrument raw data (like `.txt` files), the app will attempt to auto-map "Carico" (Load) and "Deformazione" (Extension). If a "Sforzo" (Stress) column is found, it is used to ensure 100% accuracy relative to the instrument.

### 3. Validation & Peak Detection
Open the **"Adjust & Preview"** expander. Move the sliders until the **red dotted line** tracks the initial linear slope. The app automatically truncates data at the maximum stress point.

### 4. Export
Download the **Official Report**. The resulting Excel file contains individual sample properties and a dedicated **Batch Statistics** sheet ($n, \mu, \sigma$).

---

## ✍️ Author
**Solomon Dufera Tolcha** *PhD in Mechanical Engineering*
