from fastapi import FastAPI, UploadFile, HTTPException, Query, Depends, Security
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
import os
from dotenv import load_dotenv
import aspose.threed as a3d
import io
from PIL import Image
import httpx

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
API_KEY = os.getenv("API_KEY")
UPSCALER_URL = "https://api.stability.ai/v2beta/stable-image/upscale/fast"
BG_REMOVER_URL = "https://api.stability.ai/v2beta/stable-image/edit/remove-background"
STABLE_FAST_3D_URL = "https://api.stability.ai/v2beta/3d/stable-fast-3d"

api_key_header = APIKeyHeader(name='X-API-Key', auto_error=False)

def validate_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(status_code=401, detail='Missing API Key')
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail='Invalid API Key')
    
    return api_key


def check_and_resize_image(image_data: bytes, min_pixels: int, max_pixels: int) -> bytes:
    with Image.open(io.BytesIO(image_data)) as img:
        width, height = img.size
        total_pixels = width * height
        
        if total_pixels < min_pixels or total_pixels > max_pixels:
            
            scale_factor = (max_pixels / total_pixels) ** 0.5
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            img = img.resize((new_width, new_height), Image.LANCZOS)
            
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="JPEG")
            return img_byte_arr.getvalue()
        
        return image_data
    

async def upscale(image_data: bytes) -> bytes:
    image_data = check_and_resize_image(image_data, min_pixels=1024, max_pixels=1048576)

    headers = {
        "authorization": f"Bearer {STABILITYAI_API_KEY}",
        "accept": "image/*"
    }
    files = {"image": image_data}
    data = {"output_format": "webp"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(UPSCALER_URL, headers=headers, files=files, data=data)
            response.raise_for_status()
            return response.content

    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="The request to Upscaling API timed out.")

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Upscaling failed: {e.response.text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def remove_bg(image_data: bytes) -> bytes:
    image_data = check_and_resize_image(image_data, min_pixels=4096, max_pixels=4194304)
    headers = {
        "authorization": f"Bearer {STABILITYAI_API_KEY}",
        "accept": "image/*"
    }
    files = {"image": image_data}
    data = {"output_format": "webp"}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(BG_REMOVER_URL, headers=headers, files=files, data=data)
            response.raise_for_status()
            return response.content

    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="The request to Background Removal API timed out.")

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Background Removal failed: {e.response.text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


async def convert_to_3d(image_data: bytes) -> bytes:
    image_data = check_and_resize_image(image_data, min_pixels=4096, max_pixels=4194304)
    headers = {
        "authorization": f"Bearer {STABILITYAI_API_KEY}"
    }
    files = {"image": image_data}

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(STABLE_FAST_3D_URL, headers=headers, files=files)
            response.raise_for_status()
            return response.content

    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="The request to Image-to-3D API timed out.")

    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"3D Conversion failed: {e.response.text}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@app.get("/")
async def health_check(api_key: str = Depends(validate_api_key), device_type: str = Query(..., description="Device type: 'ios' or 'android")):
    return {"health": True, "device_type": device_type}


# Query - to access query params from url
@app.post("/image-to-3d-pipeline")
async def run_pipeline(image: UploadFile, api_key: str = Depends(validate_api_key), device_type:str = Query(..., description="Device type: 'ios' or 'android")):

    if device_type.lower() not in ['android', 'ios']:
        raise HTTPException(status_code=400, detail='Invalid device_type. Must be "ios" or "android"')

    if not image.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload a PNG, JPG, JPEG, or WebP image.")

    try:
        image_data = await image.read()
        
        upscaled_image = await upscale(image_data)
        no_bg_image = await remove_bg(upscaled_image)
        model_3d = await convert_to_3d(no_bg_image)

        # Load GLB file in-memory
        glb_memory = io.BytesIO(model_3d)
        glb_memory.seek(0)

        if device_type.lower() == 'android':
            return StreamingResponse(glb_memory, media_type="model/gltf-binary", headers={"Content-Disposition": "attachment; filename=3d_model.glb"})
        
        scene = a3d.Scene()
        scene.open(glb_memory)
        usdz_memory = io.BytesIO()
        scene.save(usdz_memory, a3d.FileFormat.USDZ)
        usdz_memory.seek(0)

        return StreamingResponse(usdz_memory, media_type="model/vnd.usdz+zip", headers={"Content-Disposition": "attachment; filename=3d_model.usdz"})

    except Exception as e:
        print(f"Error in run_pipeline: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An error occurred during processing: {str(e)}")
    

# uvicorn main:app --reload --port 8000
# ./ngrok http --url https://primate-wise-longhorn.ngrok-free.app 8000
