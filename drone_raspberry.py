import base64
import json
import os
import shutil
import time
import requests
import serial
from PIL import Image
import torch
import torch.nn as nn
from torchvision import transforms
import timm

# -------------------- CONFIGURATION --------------------
# NOTE: API keys and database endpoints are left blank for public repository security.

GEMINI_API_KEY = ""
FIREBASE_BASE_URL = ""

COMMAND_URL = f"{FIREBASE_BASE_URL}/drone_control.json"
REPORT_URL = f"{FIREBASE_BASE_URL}/plant_reports.json"
GEMINI_REST_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"

# Anomaly Threshold tuned for your local autoencoder
ANOMALY_THRESHOLD = 0.030
# --------------------------------------------------------

# Initialize Device & Local Autoencoder Model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

class TinyLeafAutoencoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = timm.create_model('vit_tiny_patch16_224', pretrained=False, num_classes=0)
        self.decoder_proj = nn.Linear(192, 128 * 14 * 14)
        self.decoder = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.ConvTranspose2d(32, 16, kernel_size=4, stride=2, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.ConvTranspose2d(16, 3, kernel_size=4, stride=2, padding=1),
            nn.Sigmoid()
        )

    def forward(self, x):
        features = self.encoder(x)
        x = self.decoder_proj(features)
        x = x.view(-1, 128, 14, 14)
        return self.decoder(x)

print("Loading local autoencoder model weights on Pi...")
model = TinyLeafAutoencoder().to(device)
model_path = "healthy_tiny_autoencoder.pth"
if os.path.exists(model_path):
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    print("Local AI model ready!")
else:
    print(f"[Warning] Weights file '{model_path}' not found. Local checking will fail unless weights are present.")

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

# Initialize Flight Controller Serial Port
try:
    fc_serial = serial.Serial("/dev/ttyAMA0", baudrate=115200, timeout=1)
except Exception as e:
    print(f"[UART Warning] Flight controller port skipped: {e}")


def capture_photos(num_photos=3):
    """Captures images using rpicam/libcamera."""
    image_paths = []
    camera_cmd = "rpicam-still" if shutil.which("rpicam-still") else "libcamera-still"

    for i in range(num_photos):
        filename = f"scan_angle_{i + 1}.jpg"
        cmd = f"{camera_cmd} -o {filename} --width 1920 --height 1080 -t 500 --nopreview"
        os.system(cmd)
        image_paths.append(filename)
        time.sleep(3)  # Interval during 12-second position hold

    return image_paths


def encode_image_to_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def run_local_anomaly_check(image_path):
    """Runs local reconstruction error check using the Vision Transformer Autoencoder."""
    try:
        image = Image.open(image_path).convert("RGB")
        input_tensor = transform(image).unsqueeze(0).to(device)
        with torch.no_grad():
            reconstructed = model(input_tensor)
            error_score = torch.mean((reconstructed - input_tensor) ** 2).item()
        print(f"-> Local Model Check [{image_path}] Error Score: {error_score:.5f}")
        return error_score > ANOMALY_THRESHOLD
    except Exception as e:
        print(f"Error running local model on {image_path}: {e}")
        return True # Fallback to cloud if local check errors out


def analyze_plant_health(image_paths):
    """Locally filters photos; sends only anomalous/diseased images to Gemini API."""
    flagged_images = []
    for img in image_paths:
        if run_local_anomaly_check(img):
            print(f"    [!] Anomaly detected locally in {img}. Flagging for cloud analysis.")
            flagged_images.append(img)
        else:
            print(f"    [✓] {img} verified healthy locally. Skipping cloud upload.")

    # If all photos are healthy, bypass Gemini entirely to save tokens and time!
    if not flagged_images:
        print("-> All captured foliage verified pristine by edge model. Zero anomalies found.")
        return json.dumps({
            "anomaly_detected": "Healthy",
            "cure_and_treatment": "No treatment required. Crops are flourishing within baseline parameters.",
            "confidence_score": 1.0
        })

    print(f"-> Escalating {len(flagged_images)} flagged image(s) to Gemini API for diagnostic classification...")
    prompt_text = """
    Analyze these crop images captured by drone.
    Identify diseases, pests, or nutrient deficiencies.
    Return ONLY JSON with these exact keys:
    "anomaly_detected": (String name of disease/illness or 'Healthy'),
    "cure_and_treatment": (Detailed medicine name, dosage, and spray instructions),
    "confidence_score": (Float value between 0.0 and 1.0)
    """

    contents_parts = [{"text": prompt_text}]
    for img in flagged_images:
        base64_data = encode_image_to_base64(img)
        contents_parts.append({
            "inline_data": {"mime_type": "image/jpeg", "data": base64_data}
        })

    payload = {
        "contents": [{"parts": contents_parts}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "response_schema": {
                "type": "OBJECT",
                "properties": {
                    "anomaly_detected": {"type": "STRING"},
                    "cure_and_treatment": {"type": "STRING"},
                    "confidence_score": {"type": "NUMBER"},
                },
                "required": [
                    "anomaly_detected",
                    "cure_and_treatment",
                    "confidence_score",
                ],
            },
        },
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(
        GEMINI_REST_URL, headers=headers, json=payload, timeout=30
    )

    if response.status_code == 200:
        res_data = response.json()
        return res_data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        raise Exception(f"Error communicating with Gemini API: {response.text}")


def execute_drone_mission(target_coords):
    print("\n--- EXECUTING DRONE FLIGHT SCAN ---")
    lat = target_coords.get("lat", "N/A")
    lon = target_coords.get("lon", "N/A")
    print(f"Target Waypoint Coordinates Received -> Lat: {lat}, Lon: {lon}")
    
    print("1. Commanding Drone: Navigate to coordinates and ascend to 1 meter...")
    time.sleep(2)

    print("2. Holding position for 12 seconds & taking pictures...")
    photos = capture_photos(num_photos=3)  # Takes photos over ~12s

    print("3. Commanding Drone: Initiating slow descent and landing...")
    time.sleep(3)

    print("4. Running local edge AI filter & analyzing images...")
    report_json = analyze_plant_health(photos)

    print("5. Syncing results to Firebase...")
    payload = json.loads(report_json)
    payload["timestamp"] = int(time.time() * 1000)
    payload["coordinates"] = target_coords  # Include coordinates in the report
    requests.post(REPORT_URL, json=payload)
    print("--- MISSION COMPLETE ---\n")


def listen_loop():
    print("Pi Listener active. Polling Firebase for Launch Command...")
    while True:
        try:
            response = requests.get(COMMAND_URL, timeout=5)
            if response.status_code == 200 and response.json():
                cmd_data = response.json()
                if cmd_data.get("status") == "START":
                    print(" WEBSITE LAUNCH SIGNAL RECEIVED!")
                    # Extract target coordinates sent from the web map interface
                    target_coords = {
                        "lat": cmd_data.get("lat"),
                        "lon": cmd_data.get("lon")
                    }
                    requests.patch(COMMAND_URL, json={"status": "PROCESSING"})
                    execute_drone_mission(target_coords)
                    requests.patch(COMMAND_URL, json={"status": "IDLE"})
        except Exception as e:
            print(f"Polling check error: {e}")

        time.sleep(2)


if __name__ == "__main__":
    listen_loop()
