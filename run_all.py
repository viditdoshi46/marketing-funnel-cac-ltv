"""
Reproduce the analysis data.
  python run_all.py     # writes data/channel_summary.csv, data/funnel.csv
Then:  streamlit run app/streamlit_app.py
"""
import subprocess, sys
print("=== Generate channel economics + funnel ===")
if subprocess.run(["python", "src/make_data.py"]).returncode != 0:
    sys.exit("make_data failed")
print("\nDone. Run:  streamlit run app/streamlit_app.py")
