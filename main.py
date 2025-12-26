
from fastapi import FastAPI, UploadFile, File
from EEG_Processor import EEGProcessor
import shutil
import os

app = FastAPI()
# I am hardcoding this sampling rate for this particular dataset, but can be made flexible
processor = EEGProcessor(sfreq=250) 

@app.post("/upload")
async def upload_eeg(file: UploadFile = File(...)):
    """ Function to upload the EEG data to the backend"""
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        analysis = processor.process_csv(temp_path)
        return analysis
    finally:
        os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)