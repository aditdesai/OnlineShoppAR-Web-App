from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from dotenv import load_dotenv
import aspose.threed as a3d
import io
from PIL import Image
import uuid

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STABILITYAI_API_KEY = os.getenv("STABILITYAI_API_KEY")
UPSCALER_URL = "https://api.stability.ai/v2beta/stable-image/upscale/fast"
BG_REMOVER_URL = "https://api.stability.ai/v2beta/stable-image/edit/remove-background"
STABLE_FAST_3D_URL = "https://api.stability.ai/v2beta/3d/stable-fast-3d"


def check_and_resize_image(image_data: bytes, min_pixels: int, max_pixels: int) -> bytes:
    with Image.open(io.BytesIO(image_data)) as img:
        width, height = img.size
        total_pixels = width * height
        
        if total_pixels < min_pixels or total_pixels > max_pixels:
            
            scale_factor = (max_pixels / total_pixels) ** 0.5
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            img = img.resize((new_width, new_height), Image.ANTIALIAS)
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG")
            return img_byte_arr.getvalue()
        
        return image_data
    

def upscale(image_data: bytes) -> bytes:
    image_data = check_and_resize_image(image_data, min_pixels=1024, max_pixels=1048576)

    headers = {
        "authorization": f"Bearer {STABILITYAI_API_KEY}",
        "accept": "image/*"
    }
    files = {"image": image_data}
    data = {"output_format": "webp"}
    response = requests.post(UPSCALER_URL, headers=headers, files=files, data=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Upscaling failed: {response.json()}")
    
    return response.content


def remove_bg(image_data: bytes) -> bytes:
    image_data = check_and_resize_image(image_data, min_pixels=4096, max_pixels=4194304)
    headers = {
        "authorization": f"Bearer {STABILITYAI_API_KEY}",
        "accept": "image/*"
    }
    files = {"image": image_data}
    data = {"output_format": "webp"}
    response = requests.post(BG_REMOVER_URL, headers=headers, files=files, data=data)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"Background removal failed: {response.json()}")
    
    return response.content


def convert_to_3d(image_data: bytes) -> bytes:
    image_data = check_and_resize_image(image_data, min_pixels=4096, max_pixels=4194304)
    headers = {
        "authorization": f"Bearer {STABILITYAI_API_KEY}"
    }
    files = {"image": image_data}
    response = requests.post(STABLE_FAST_3D_URL, headers=headers, files=files)
    
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail=f"3D conversion failed: {response.json()}")
    
    return response.content


@app.get("/")
async def health_check():
    return {"health": True}


@app.post("/image-to-3d-pipeline")
async def run_pipeline(image: UploadFile):
    if not image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PNG, JPG, JPEG, or WebP image.")

    try:
        image_data = await image.read()
        
        upscaled_image = upscale(image_data)
        no_bg_image = remove_bg(upscaled_image)
        model_3d = convert_to_3d(no_bg_image)

        glb_memory = io.BytesIO(model_3d)
        
        unique_id = uuid.uuid4()
        temp_glb_path = f"./temp_model-{unique_id}.glb"
        
        with open(temp_glb_path, "wb") as temp_file:
            temp_file.write(glb_memory.getvalue())

        scene = a3d.Scene.from_file(temp_glb_path)
        
        usdz_memory = io.BytesIO()
        scene.save(usdz_memory, a3d.FileFormat.USDZ)
        
        os.remove(temp_glb_path)

        usdz_memory.seek(0)

        return StreamingResponse(usdz_memory, media_type="model/vnd.usdz+zip", headers={"Content-Disposition": "attachment; filename=3d_model.usdz"})

    except Exception as e:
        print(f"Error in run_pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during processing: {str(e)}")