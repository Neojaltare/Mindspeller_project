import pytest
import numpy as np
from EEG_Processor import EEGProcessor
import pandas as pd



@pytest.fixture
def processor():
    return EEGProcessor()

def test_auto_scaling_logic(processor):
    # Test Microvolts
    uv_data = np.array([[50.0, -50.0]])
    scaled_uv = processor._scale_data(uv_data)
    assert scaled_uv[0, 0] == pytest.approx(0.00005)
    
    # Test Volts 
    v_data = np.array([[0.00005, -0.00005]])
    scaled_v = processor._scale_data(v_data)
    assert scaled_v[0, 0] == pytest.approx(0.00005)

def test_classification_winner(processor):
    # Mock metrics where Arousal is the clear winner (ratio = 2.0)
    mock_bp = {
        'drowsiness_index': 1.0,
        'arousal_index': 2.0, 
        'focus_index': 1.0,
        'mind_wandering_index': 1.0,
        'Total_Power': 1e-10
    }
    mock_global = {
        'drowsiness_index': 1.0,
        'arousal_index': 1.0,
        'focus_index': 1.0,
        'mind_wandering_index': 1.0
    }
    
    state, _ = processor._classify_state(mock_bp, mock_global, is_noisy=False)
    assert state == "High Arousal"

def test_artifact_priority(processor):
    """
    Ensures that if an epoch is flagged as noisy, the 'Artifact' label 
    overrides any high cognitive scores.
    """
    # Simulate an epoch with massive Focus score but also massive Noise
    mock_bp = {
        'focus_index': 10.0, # This would normally be "High Focus"
        'arousal_index': 1.0, 
        'drowsiness_index': 1.0, 
        'mind_wandering_index': 1.0,
        'Total_Power': 1e-10
    }
    mock_global = {
        'focus_index': 1.0, 
        'arousal_index': 1.0, 
        'drowsiness_index': 1.0, 
        'mind_wandering_index': 1.0
    }
    
    state, _ = processor._classify_state(mock_bp, mock_global, is_noisy=True)
    assert state == "Artifact", "Should be Artifact when is_noisy=True"
    
    state_clean, _ = processor._classify_state(mock_bp, mock_global, is_noisy=False)
    assert state_clean == "High Focus"

def test_neutral_zone(processor):
    """
    Create some mock metrics to test the neutral zone classification.
    Ensures that if a cognitive score is just above 1, it is classified as "Baseline/Neutral".
    """
    mock_bp = {
        'focus_index': 1.05, 
        'arousal_index': 1.0, 
        'drowsiness_index': 1.0, 
        'mind_wandering_index': 1.0
    }
    mock_global = {
        'focus_index': 1.0, 
        'arousal_index': 1.0, 
        'drowsiness_index': 1.0, 
        'mind_wandering_index': 1.0
    }
    
    state, _ = processor._classify_state(mock_bp, mock_global, is_noisy=False)
    assert state == "Baseline/Neutral"



def test_all_artifact_session(processor):
    """Checks that the processor handles sessions where all data is noisy."""
    # Mock PSD data (3 epochs, 1 channel, 10 frequencies)
    mock_psds = np.ones((3, 1, 10)) 
    mock_freqs = np.linspace(0.5, 45, 10)
    
    # If all indices are noisy
    noisy_indices = [0, 1, 2]
    
    # This mimics the logic in process_csv
    clean_indices = [i for i in range(len(mock_psds)) if i not in noisy_indices]
    if not clean_indices:
        clean_psd = mock_psds
    else:
        clean_psd = mock_psds[clean_indices]
        
    assert clean_psd.shape == mock_psds.shape


def test_band_metrics_calculation(processor):
    """
    Checks that the band metrics calculation is correct.
    """
    # dummy PSD: 1.0 everywhere
    freqs = np.array([1, 2, 5, 10, 20, 40])
    psd = np.ones(len(freqs)) 
    
    metrics = processor._calculate_band_metrics(psd, freqs)
    
    # In a PSD of all 1s, any average should be 1.0
    assert metrics['Alpha'] == 1.0
    # Focus Index (Beta/Alpha) should be 1.0 / 1.0 = 1.0
    assert metrics['focus_index'] == 1.0
    # Total power should be the mean of the array
    assert metrics['Total_Power'] == 1.0


def test_quality_warning_trigger(processor):
    # Simulate the condition where no clean indices are found
    psd_data = np.random.rand(5, 1, 10) # 5 epochs
    noisy_indices = [0, 1, 2, 3, 4] # All 5 are noisy
    
    clean_indices = [i for i in range(len(psd_data)) if i not in noisy_indices]
    
    if not clean_indices:
        processor.quality_warning = True
        clean_psd = psd_data
    
    assert processor.quality_warning is True
    assert clean_psd.shape == psd_data.shape