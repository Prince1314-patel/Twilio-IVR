from fastapi import APIRouter, UploadFile, File

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    # TODO: Integrate Groq Whisper for speech-to-text
    # audio_data = await file.read()
    # transcription = whisper_transcribe(audio_data)
    # return {"text": transcription}
    return {"text": "[Transcription placeholder]"} 