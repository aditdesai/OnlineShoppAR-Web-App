import requests

url = "http://127.0.0.1:8000/image-to-3d-pipeline"
image_path = "chair-2.jpg"

with open(image_path, "rb") as image_file:
    files = {"image": image_file}
    response = requests.post(url, files=files)

if response.status_code == 200:
    # Save the USDZ file response
    with open("output.usdz", "wb") as f:
        f.write(response.content)
    print("USDZ file saved as output.usdz")
else:
    print("Failed to process image:", response.json())
