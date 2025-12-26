

My Approach to the Architecture

I decided to go with sstreamlit for the front end and fastapi and uvicorn for the back end. There may be better ways to set this up but I thought this was perhaps enough for the purpose of this project. I should mention that I dont have any training in full stack, especially front end development. But I learn quickly, and if I need to do a lot of full stack development, Im happy to learn on the job. I dont think it will be too much of a problem. 

Keeping things responsive: EEG processing, especially with MNE-Python, can be pretty heavy on the CPU. By running the signal processing on a dedicated backend, the UI stays fast and doesn't freeze up while the math is happening.



Signal pre-processing

I used MNE for all the signal processing since this was quicker and there is a lot of flexibility with MNE. And given the time frame of two days, this seemed appropriate. 

MNE-Python expects data in Volts. I added an auto-scaling check so that if the input is in microvolts (which is common for probably most recording software), the system detects that and scales it down automatically.

Filtering: I used an FIR bandpass filter set to 0.5–45Hz. This knocks out the slow-wave drift and that annoying 50/60Hz powerline noise. Particularly because most of the frequencies I was interested in are contained within this range. 

Referencing: I applied an Average Reference to the 14 channel data. This is not something I would usually do because you usually want full electrode coverage. But I wanted to emphasise local activity, and at least we have 14 channels spread over the acalp. This emphasis on local activity can be useful when we want to leverage localised changes in EEG activity. 

Noise Detection: I have left out bad electrode identification or any advanced algorithms like ICA. Since it is a short recording anyway and may not be enough for ICA and if we want the application to run quickly, better to stay simple. I am simply identifying bad data based on large peak to peak values, high standard deviation and also high over signal power. These are quite simple to compute and standard methods. I also have defined an arbitrary threshold of 30% of channels as being the minimum criteria for throwing out a full epoch. I didnt want to discard the entire epoch if only some channels were bad, especially since I am computing metrics based on global averages and not leveraging spatial information. However, this is something that could easily be done since we have channel names and locations.  



Mapping EEG Features to Cognitive States

As per your instructions, I segmented the 3-minute sessions into 30-second windows. To make the system robust across different users, I moved away from absolute power and focused on Spectral Ratios. This was also based on literature which I have briefly cited here.

Arousal (β/θ): I used the Beta/Theta ratio to track cortical activation and physiological arousal levels. High values in this ratio generally correlate with increased alertness and emotional or cognitive intensity.

High Focus (β/α): I track the Beta/Alpha ratio. Since high Beta activity is a hallmark of cortical engagement, this ratio effectively captures when a brain is "switched on" and task-oriented.

Drowsiness (θ/α): I monitor the Theta/Alpha ratio. As alertness dips, Theta power tends to rise relative to Alpha, making this a reliable marker for fatigue or decreased vigilance.

Mind Wandering (θ/β): I utilized the Theta/Beta ratio (TBR). This is a well-established scientific marker for task-unrelated thought, internal distraction, or a drop in executive control.


Adaptive Baselining: To ensure the scores are personalized, I calculate a "Clean Baseline" (global average across the entire recording) for each of the metrics using only the non-noisy segments of the session. By comparing each window to the user's own session average rather than a generic "human average," the system accounts for individual physiological changes through the session. I chose the global average since we dont have a dedicated or appropriate baseline period. I calculate each metric as a ratio of their baseline (average) metric. This also has the advantage of making the scores more interpretable. They can be interpreted as periods where that cognitive state was likely to be higher or lower by a certian interpretable amount relative to their session average.



Artifact Detection

I set up a Peak-to-Peak (PTP) check. If a window swings more than 300μV, the system flags it as an "Artifact." This prevents muscle movements from being incorrectly labeled as "High Focus." I have left out blink detection here since I usually use ICA for that. But with more time, I could add some standard method that could reasonably well identify blinks without the use of a dedicated EOG channel. I also wanted to avoid a total application crash if the data quality was poor. If a file is 100% noisy (artifact), the system falls back to the full dataset for its baseline calculation but triggers a quality_warning in the UI. It’s a transparent way of telling the user: "The signal was messy, so treat these specific results with caution."



Data Source

dI used the Albasri (2019) Mendeley Dataset which seemed to perfectly fit the requirements of the project. It was the perfect choice for this task because the protocol specifically recorded subjects switching between relaxation and concentration tasks in 3-minute blocks—mirroring exactly what I’m trying to detect. I also tailored the backend to match the dataset's EMOTIV EPOC+ hardware specs, specifically setting the sampling rate to 250Hz and aligning the channel configurations to ensure the simulation was as realistic as possible. This code is therefore not flexible in detecting these parameters from the data, but this can be done as well quite easily. 

Dataset Reference: * Albasri (2019): "EEG dataset of Fusion relaxation and concentration moods." Mendeley Data, V1, doi: 10.17632/8c26dn6c7w.1.