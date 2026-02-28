from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from static_backend import app as langgraph_app, key_manager
from groq_key_manager import AllKeysExhaustedError
from scan_config import should_skip_file, SKIP_FOLDERS
import logging

logger = logging.getLogger(__name__)

fastapi_app = FastAPI()

# Enable CORS
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")


@fastapi_app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


@fastapi_app.get("/skip-folders")
async def get_skip_folders():
    """Return the list of folder names that should be skipped during scanning."""
    return {"skip_folders": [f.lower() for f in SKIP_FOLDERS]}


@fastapi_app.post("/analyze")
async def analyze_code(files: List[UploadFile] = File(...)):
    results = []
    skipped_count = 0
    
    for file in files:
        # Skip non-Python files
        if not file.filename.endswith(".py"):
            continue
        
        # Skip files inside excluded folders (server-side safety net)
        if should_skip_file(file.filename):
            skipped_count += 1
            logger.info("Skipped file from excluded folder: %s", file.filename)
            continue
        
        try:
            # Read file content
            content = await file.read()
            file_content = content.decode("utf-8")
            
            # Pass to LangGraph workflow
            result = langgraph_app.invoke({"code": file_content})
            
            results.append({
                "filename": file.filename,
                "report": result["final_report"],
                "fixed_code": result["fixed_code"]
            })

        except AllKeysExhaustedError as e:
            # All API keys are rate-limited — stop processing further files
            logger.error("All API keys exhausted while processing '%s': %s", file.filename, e)
            results.append({
                "filename": file.filename,
                "report": (
                    "⚠️ All available Groq API keys have been rate-limited. "
                    "Processing stopped at this file. Please wait a few minutes and try again."
                ),
                "fixed_code": ""
            })
            break  # no point trying remaining files

        except Exception as e:
            logger.exception("Error processing '%s'", file.filename)
            results.append({
                "filename": file.filename,
                "report": f"Error processing file: {str(e)}",
                "fixed_code": ""
            })
    
    if not results:
        raise HTTPException(status_code=400, detail="No .py files found in the uploaded folder")
    
    return {"results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000)
