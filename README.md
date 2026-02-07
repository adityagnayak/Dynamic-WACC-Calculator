# Dynamic-WACC-Calculator
This is a repository for a single file WACC Calculator accounting for foreign as well as local capital sources.
# 📊 Dynamic WACC Calculator

A highly interactive financial modeling tool built with **Streamlit**. This application calculates a firm's **Weighted Average Cost of Capital (WACC)** with dynamic inputs for multiple debt sources and a visual, reactive formula display.

## 🚀 Features

* **Dynamic Inputs:** Add as many local or foreign debt sources as needed; the app adjusts automatically.
* **Reactive Formula:** The mathematical formula `WACC = (E/V * Re) + (D/V * Rd * (1 - T))` is displayed on-screen. As you input data, the relevant terms in the formula **light up** in green to show active variables.
* **Transparent Logic:** A dedicated "View Calculation Logic" section displays the underlying Python code used for the math.
* **Instant Calculation:** Real-time updates for Total Equity, Total Debt, and Firm Value.

## 🛠️ Installation & Local Run

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/wacc-calculator.git](https://github.com/your-username/wacc-calculator.git)
    cd wacc-calculator
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the app:**
    ```bash
    streamlit run wacc_app.py
    ```

## ☁️ Deployment (Streamlit Community Cloud)

1.  Push this code to a GitHub repository.
2.  Go to [share.streamlit.io](https://share.streamlit.io/).
3.  Connect your GitHub account.
4.  Select this repository and the `wacc_app.py` file.
5.  Click **Deploy**.

## 📂 Project Structure

* `wacc_app.py`: The main application script containing UI and logic.
* `requirements.txt`: List of Python dependencies (`streamlit`, `pandas`).

---

## ⚡ Vibe Code Disclosure

**Status:** `Flow State`  
**Aesthetic:** `Clean / Minimalist / Reactive`

This codebase was crafted with a philosophy of **Radical Transparency**. 
* **No Black Boxes:** The math is visualized in real-time.
* **User-Centric:** The UI reacts to the user, not the other way around.
* **Maintenance:** The code is written in a single file for maximum portability and ease of understanding. It is designed to be forked, broken, fixed, and improved.

*Built for financial modelers who prefer code over spreadsheets.*
