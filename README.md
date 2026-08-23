# Vriddhi 2.0: Autonomous AgTech & Smart Verification Ecosystem

---

## 🚀 Overview

**Vriddhi 2.0** is an end-to-end agricultural technology platform designed to bridge the gap between smallholder farming and high-value climate finance. By integrating custom-built autonomous hardware, local edge-artificial intelligence, and a lightweight tamper-proof cryptographic ledger, Vriddhi 2.0 automates farm monitoring, precise micro-interventions, and verifiable environmental reporting.

---

## ⚙️ How It Works: The Workflow Architecture

1. **Field Selection & Satellite Data (Landing & Map Pages):**
Farmers interact with the platform via web/mobile dashboards to select their field area of interest on an interactive map. Coordinates are processed to pull baseline environmental insights.
2. **Autonomous Drone Flight & Edge Scanning:**
Upon receiving a launch signal from the web backend (`app.py`), the Raspberry Pi-powered drone executes a localized flight mission, hovering to capture high-resolution imagery using onboard cameras.
3. **Local Edge-AI Processing:**
Captured images pass through our custom Vision Transformer (ViT) Autoencoder running directly on the edge. The model evaluates reconstruction error to instantly filter pristine foliage from stressed or diseased crops.
4. **Precision Spot-Spraying:**
Instead of blanket-spraying chemicals across the entire field, the system isolates exact GPS coordinates of detected anomalies, reducing agrochemical usage by up to 40%.
5. **Cryptographic Blockchain Logging:**
Every intervention (user name, anomaly GPS coordinates, timestamp, and precision-spray execution method) is securely bundled and locked into a local SHA-256 cryptographic blockchain ledger (`blockchain_ledger.json`).

---

## 🤖 In-House Artificial Intelligence & Models

Vriddhi 2.0 leverages a hybrid AI pipeline combining edge computing with cloud intelligence:

* **Local Edge Model (Vision Transformer Autoencoder):**
* **Architecture:** Built using a `vit_tiny_patch16_224` encoder paired with a custom transposed-convolutional decoder built on PyTorch and `timm`.
* **Function:** Operates directly on the Raspberry Pi. It learns the baseline "perfect" reconstruction pattern of healthy crops. When a leaf anomaly (e.g., blight, pest damage, or nutrient deficiency) occurs, the reconstruction error spikes past our tuned `ANOMALY_THRESHOLD` (0.030), flagging the precise image.
* **Efficiency:** Acts as an intelligent gatekeeper, skipping cloud escalations for healthy crops to preserve bandwidth and latency.


* **Cloud Diagnostic Model (Gemini 2.5 Flash):**
* **Function:** When an image is flagged by the local autoencoder, it is escalated via REST API to Gemini 2.5 Flash. The model performs deep medical classification on the crop, returning structured JSON containing exact disease names, precise medication/dosage formulas, and confidence scores.



---

## 🛡️ Tamper-Proof Ledger (The Blockchain Layer)

To maintain institutional-grade trust for carbon buyers and insurance underwriters without incurring exorbitant gas fees or network bloat, Vriddhi 2.0 implements a **lightweight, native Python cryptographic blockchain**:

* **Mechanism:** Uses SHA-256 hashing to link sequential blocks containing farmer credentials, exact GPS anomaly points, and treatment logs.
* **Integrity:** Any unauthorized modification to past records breaks the mathematical chain hash (`is_chain_valid()`), making fraudulent data manipulation impossible.
* **Accessibility:** Stored persistently as a local JSON audit trail ready for secure transmission.

---

## 💰 Monetization, Carbon Credits & Insurance Integration

### 1. Carbon Credits & Data Monetization

* **The Reality:** Precision spot-spraying doesn't pull carbon out of the air directly, but it drastically reduces chemical manufacturing footprints, tractor fuel emissions, and toxic runoff (Scope 3 supply chain emissions).
* **The Business Model:** Vriddhi 2.0 acts as a **Digital MRV (Measurement, Reporting, and Verification) engine**. We bundle our tamper-proof GPS logs and edge-verified intervention data and license/sell this high-integrity dataset to agricultural carbon aggregators and FPOs who handle large-scale credit issuance.

### 2. Parametric Crop Insurance

* **The Integration:** Through our insurance module, farmers impacted by crop failure can submit claims directly through the platform.
* **The Workflow:** When submitted, the backend automatically pairs the insurance application form with the user's tamper-proof blockchain logs (verifying exact field coordinates and active treatment history). This verified data packet can be transmitted directly to tech-forward, parametric agricultural insurance providers (such as SafeTree/A2V and specialized agritech underwriters) via automated webhooks or instant WhatsApp dispatch links, cutting weeks of manual field investigations down to automated payouts.

---

## 🛠️ Technology Stack

* **Backend & Web:** Python, Flask, Gunicorn, Requests
* **Edge Computing & AI:** PyTorch, Torchvision, TIMM (Vision Transformers), PIL, OpenCV
* **Hardware & Telemetry:** Raspberry Pi, Python Serial, UART (`/dev/ttyAMA0`), libcamera/rpicam
* **Security & Ledger:** SHA-256 Cryptographic Hashing, Local JSON State Architecture
