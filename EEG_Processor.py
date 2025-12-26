import pandas as pd
import numpy as np
import mne

class EEGProcessor:
    def __init__(self, sfreq=250, window_size=30):
        self.sfreq = sfreq  # 250Hz for Emotiv EPOC+
        self.window_size = window_size  # 30 seconds window size
        self.quality_warning = False
        self.bands = {
            'Delta': (0.5, 4),
            'Theta': (4, 8),
            'Alpha': (8, 13),
            'Beta': (13, 30),
            'Gamma': (30, 45)
        }
    
    def process_csv(self, file_path):
        """Main function to process the EEG data and produce the output."""
        df = pd.read_csv(file_path)
        raw = self._prepare_raw_data(df)
        
        # Windowing
        events = mne.make_fixed_length_events(raw, duration=self.window_size)
        epochs = mne.Epochs(raw, events, tmin=0, tmax=self.window_size, 
                            baseline=None, preload=True, verbose=False)

        # PSD Calculation
        psds_obj = epochs.compute_psd(method='welch', fmin=.5, fmax=45, verbose=False)
        psd_data = psds_obj.get_data() 
        freqs = psds_obj.freqs

        # Identify Artifacts
        noisy_indices = self.get_noisy_epoch_indices(epochs)
        
        # Calculate Global Baseline (Clean epochs only)
        clean_indices = [i for i in range(len(psd_data)) if i not in noisy_indices]
        if not clean_indices:
            # Fallback to all data but flag a warning
            clean_psd = psd_data
            self.quality_warning = True
        else:
            self.quality_warning = False
            clean_psd = psd_data[clean_indices]
            
        global_avg_spectrum = clean_psd.mean(axis=(0, 1))
        global_avg_metrics = self._calculate_band_metrics(global_avg_spectrum, freqs)

        # Classification Loop for each epoch classification
        results, scores_list = [], []
        for i in range(len(psd_data)):
            epoch_spectrum = psd_data[i].mean(axis=0)
            epoch_metrics = self._calculate_band_metrics(epoch_spectrum, freqs)
            
            state, scores = self._classify_state(
                epoch_metrics, 
                global_avg_metrics, 
                is_noisy=(i in noisy_indices)
            )
            results.append(state)
            scores_list.append(scores)
            
        return self._aggregate_results(results, scores_list)

    
    def _calculate_band_metrics(self, psd_spectrum, freqs):

        metrics = {}
        for band, (fmin, fmax) in self.bands.items():
            mask = (freqs >= fmin) & (freqs <= fmax)
            metrics[band] = psd_spectrum[mask].mean()
        
        # Ratios for the different cognitive state calculations
        metrics["focus_index"] = metrics["Beta"] / metrics["Alpha"]
        metrics["mind_wandering_index"] = metrics["Theta"] / metrics["Beta"]
        metrics["arousal_index"] = metrics["Beta"] / metrics["Theta"]
        metrics["drowsiness_index"] = metrics["Theta"] / metrics["Alpha"]
        metrics["Total_Power"] = psd_spectrum.mean()
        return metrics

    def _prepare_raw_data(self, df):
        """Handles Scaling, MNE Object Creation, Filtering, and Montage."""
        eeg_cols = [col for col in df.columns if col not in ['label', 'time', 'timestamp', 'index']]
        data = self._scale_data(df[eeg_cols].values.T)
        
        info = mne.create_info(ch_names=eeg_cols, sfreq=self.sfreq, ch_types='eeg')
        raw = mne.io.RawArray(data, info, verbose=False)
        
        # Apply Montage
        montage = mne.channels.make_standard_montage('standard_1020')
        raw.set_montage(montage, on_missing='warn')
        
        # Filtering & Reference
        raw.filter(l_freq=0.5, h_freq=45.0, fir_design='firwin', verbose=False)
        raw.set_eeg_reference(ref_channels='average', projection=False, verbose=False)
        return raw

    
    def _scale_data(self, raw_values):
        """
        This function is used to scale the data to volts if the max value is > 0.1
        Since 0.1 Volts = 100,000 uV, which is impossible for raw EEG
        """
        if np.max(np.abs(raw_values)) > 0.1:
            return raw_values * 1e-6
        return raw_values


    def _classify_state(self, bp, global_avg_metrics, is_noisy=False):
            """
            Competitive classification: The state with the highest 
            ratio relative to baseline wins.
            """

            scores_dict = {
                "Drowsy": bp['drowsiness_index'] / global_avg_metrics['drowsiness_index'],
                "High Arousal": bp['arousal_index'] / global_avg_metrics['arousal_index'],
                "High Focus": bp['focus_index'] / global_avg_metrics['focus_index'],
                "Low Focus": bp['mind_wandering_index'] / global_avg_metrics['mind_wandering_index']
            }

            # Create the DataFrame for the frontend scores history
            formatted_scores = pd.DataFrame({
                "drowsiness_score": [scores_dict["Drowsy"]],
                "arousal_score": [scores_dict["High Arousal"]],
                "focus_score": [scores_dict["High Focus"]],
                "mind_wandering_score": [scores_dict["Low Focus"]]
            }, index=[0])

            # Handle Artifacts First
            if is_noisy or bp.get('Total_Power', 0) > 1e-9:
                return "Artifact", formatted_scores

            # We find which state has the maximum ratio relative to global average
            winning_state = max(scores_dict, key=scores_dict.get)
            highest_ratio = scores_dict[winning_state]

            # Threshold & Final Classification to avoid tiny fluctuations from triggering labels
            if highest_ratio < 1.15:
                return "Baseline/Neutral", formatted_scores
            
            return winning_state, formatted_scores
            
    def _aggregate_results(self, results, scores_list):
        """Creates the session profile and includes the data quality flag. This is the output used by the frontend."""
        quality_warning = self.quality_warning
        total = len(results)
        counts = pd.Series(results).value_counts().to_dict()
        profile = {state: round((count / total) * 100, 1) for state, count in counts.items()}
        
        scores_df = pd.concat(scores_list, axis=0)
        
        return {
            "session_profile": profile,
            "timeline": results,
            "metadata": {
                "windows": total, 
                "window_size_sec": self.window_size,
                "quality_warning": quality_warning 
            },
            "scores": scores_df.to_dict(orient='records') 
        }

    def get_noisy_epoch_indices(self, epochs, channel_threshold_pct=0.3):
        """ 
        This function is used to identify epochs that might be noisy
        Since I am mostly using global (scalp wide) metrics, I classify an epoch as noisy if 
        more than 30% of the channels are identified as noisy.
        This threshold can be changed. Additionally, the methods I have used here for noisy epoch identification
        are very basic, just for the sake of demonstration.
        In a real-world application, you would likely use more sophisticated methods.
        """
        
        noisy_indices = []
        data = epochs.get_data(copy=False) 
        n_epochs, n_channels, n_samples = data.shape
        
        # Threshold for how many bad channels make a bad epoch
        max_bad_channels = int(n_channels * channel_threshold_pct)

        for epoch_idx in range(n_epochs):
            bad_channels_in_epoch = []
            
            for ch_idx in range(n_channels):
                ch_data = data[epoch_idx, ch_idx, :]
                
                # Peak-to-Peak check per channel
                ptp = np.ptp(ch_data)
                
                # Channel std check
                ch_std = np.std(ch_data)

                # Define per-channel "badness"
                is_bad = False
                if ptp > 300e-6: # High amplitude (Blink/Pop)
                    is_bad = True
                elif ch_std < 1e-7: # Flatline
                    is_bad = True
                elif ch_std > 100e-6: # Major muscle/EMG noise
                    is_bad = True
                    
                if is_bad:
                    bad_channels_in_epoch.append(epochs.ch_names[ch_idx])

            
            num_bad = len(bad_channels_in_epoch)
            if num_bad > max_bad_channels:
                noisy_indices.append(epoch_idx)
                print(f"Rejected Epoch {epoch_idx}: {num_bad}/{n_channels} channels noisy. "
                    f"Bads: {bad_channels_in_epoch}")
            elif num_bad > 0:
                print(f"Epoch {epoch_idx} kept: Only {num_bad} channel(s) noisy.")

        return noisy_indices