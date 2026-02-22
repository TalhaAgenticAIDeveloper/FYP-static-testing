from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from static_backend import app as langgraph_app

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


@fastapi_app.post("/analyze")
async def analyze_code(files: List[UploadFile] = File(...)):
    results = []
    
    for file in files:
        # Skip non-Python files
        if not file.filename.endswith(".py"):
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
        except Exception as e:
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
