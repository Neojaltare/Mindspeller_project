# MindSpeller EEG Time-Window Profiler
A full-stack neuroprofiling application that transforms raw EEG telemetry into actionable cognitive insights. This project implements an end-to-end pipeline: mapping raw EEG signals to cognitive states and aggregating them into a session-wide profile.

## System Architecture

Backend: A Python-based API (running on localhost:8000) that leverages MNE-Python for high-performance signal processing, artifact detection, and spectral feature extraction.

Frontend: A Streamlit dashboard that handles file ingestion, asynchronous API communication, and interactive data visualization.


# Quickstart
# 1. Clone the repo
git clone https://github.com/Neojaltare/Mindspeller_project.git

cd MindSpeller_project

# 2. Install dependencies
pip install -r Requirements.txt

# 3. Start Backend (Terminal 1)
python main.py

# 4. Start Frontend (Terminal 2)
streamlit run app.py


1. Environment Setup
Install the core dependencies in a new conda env

See the list in Requirements.txt

2. Launch the Backend API
Open your terminal and start the processing engine. This must be running for the UI to function:

python main.py

The backend will initialize and listen for processing requests on port 8000.

3. Launch the Frontend UI

Open a new terminal tab and launch the web dashboard:

streamlit run app.py


# The Processing Pipeline
Preprocessing: Data is auto-scaled, bandpass filtered (0.5–45Hz), and average re-referenced.

Segmentation: The session is divided into 30-second windows (epochs).

Artifact Detection: Each window is screened for physiological noise (blinks, muscle activity) using Peak-to-Peak amplitude and variance thresholds.

Feature Extraction: Welch's method computes PSD to derive validated cognitive indices:

Focus: β/α ratio.

Arousal:  β/θ ratio.

Drowsiness: θ/α ratio.

Mind Wandering: θ/β ratio.

Adaptive Baselining: Metrics are normalized against the "Clean" segments of the input data to ensure person-specific variation is reflected in our output. This is provisional since we dont have any other baseline period here. 

# Validation
To run the automated unit tests:

Bash
python -m pytest
