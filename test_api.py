import requests

API_KEY = "qB_EbW1RpG7ltHBRB0tUroR9AzB62u1dVdMlEjuVooQ" 
DEVICE_TYPE = "android"

url = "http://localhost:8000/image-to-3d-pipeline"
image_path = "test image.jpg"

headers = {
    "X-API-Key": API_KEY
}

params = {
    "device_type": DEVICE_TYPE
}

with open(image_path, "rb") as image_file:
    files = {"image": image_file}
    response = requests.post(url, headers=headers, params=params, files=files)

if response.status_code == 200:
    file_extension = "usdz" if DEVICE_TYPE == "ios" else "glb"
    output_filename = f"output.{file_extension}"
    
    with open(output_filename, "wb") as f:
        f.write(response.content)
    
    print(f"File saved as {output_filename}")
else:
    print("Failed to process image:", response.json())

