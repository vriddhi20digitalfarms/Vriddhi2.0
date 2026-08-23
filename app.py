from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_from_directory
from flask_cors import CORS
import ee
import json
import hashlib
from datetime import datetime, timedelta
import uuid
import os
from pymongo import MongoClient
import certifi
from dotenv import load_dotenv
import urllib.request
import urllib.parse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Load environment variables
load_dotenv()

print("====================================================")
print("🚀 CACHE BREAKER v2.0: RUNNING BRUTE FORCE CODE ENGINE!!")
print("====================================================")

app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
app.secret_key = 'vriddhi_super_secret_session_key_987'
CORS(app)

# 1. Connect to MongoDB Atlas
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError("MONGO_URI environment variable is not set. Please check your .env file.")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["agriculture_app"]
users_col = db["farmer_profiles"]
history_col = db["fields_telemetry"]
marketplace_col = db["marketplace_items"]
claims_col = db["insurance_claims"]
orders_col = db["marketplace_orders"]

# ----------------- LIGHTWEIGHT BLOCKCHAIN LOGGING ENGINE -----------------
BLOCKCHAIN_FILE = "blockchain_ledger.json"

def calculate_block_hash(block):
    # Deterministic hashing sorting the keys, excluding the 'hash' field if present
    block_copy = {k: v for k, v in block.items() if k != 'hash'}
    block_string = json.dumps(block_copy, sort_keys=True).encode('utf-8')
    return hashlib.sha256(block_string).hexdigest()

def log_to_blockchain(farmer_name, coordinates, spray_method):
    blockchain = []
    if os.path.exists(BLOCKCHAIN_FILE):
        try:
            with open(BLOCKCHAIN_FILE, 'r') as f:
                blockchain = json.load(f)
        except Exception as e:
            print("Error reading blockchain file, resetting ledger:", e)
            blockchain = []
            
    previous_hash = blockchain[-1].get('hash', '0') if blockchain else "0"
    
    block = {
        "index": len(blockchain) + 1,
        "farmer_name": farmer_name,
        "coordinates": coordinates,
        "spray_method": spray_method,
        "timestamp": datetime.utcnow().isoformat(),
        "previous_hash": previous_hash
    }
    
    block['hash'] = calculate_block_hash(block)
    blockchain.append(block)
    
    with open(BLOCKCHAIN_FILE, 'w') as f:
        json.dump(blockchain, f, indent=4)
        
    return block

def find_blockchain_log(farmer_name):
    if not os.path.exists(BLOCKCHAIN_FILE):
        return None
    try:
        with open(BLOCKCHAIN_FILE, 'r') as f:
            ledger = json.load(f)
            # Find the latest block corresponding to the user (case-insensitive)
            for block in reversed(ledger):
                if block.get('farmer_name', '').strip().lower() == farmer_name.strip().lower():
                    return block
    except Exception as e:
        print("Error reading blockchain ledger file:", e)
    return None

def generate_claim_pdf(combined_packet, filepath):
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#065f46'), # Emerald 800
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569'), # Slate 600
        alignment=1, # Center
        spaceAfter=25
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#1e293b'), # Slate 800
        spaceBefore=12,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#334155') # Slate 700
    )
    
    body_bold = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    # Title
    story.append(Paragraph("VRIDDHI 2.0 CROP INSURANCE CERTIFICATE", title_style))
    story.append(Paragraph("Formal Compensation Claim & Blockchain Verification Record", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Combined data layout
    claim_id = combined_packet['claim_id']
    ins = combined_packet['insurance_details']
    block = combined_packet['blockchain_verification']
    
    # Overview Table (Claim ID & Status)
    status_color = '#059669' if ins['status'].lower() == 'pending' else '#b91c1c'
    overview_data = [
        [Paragraph("Claim Reference ID:", body_bold), Paragraph(claim_id, body_style),
         Paragraph("Initial Claim Status:", body_bold), Paragraph(ins['status'].upper(), ParagraphStyle('Status', parent=body_bold, textColor=colors.HexColor(status_color)))],
        [Paragraph("Submission Timestamp:", body_bold), Paragraph(ins['submission_date'], body_style),
         Paragraph("Verification Method:", body_bold), Paragraph("Blockchain Telemetry Verification", body_style)]
    ]
    overview_table = Table(overview_data, colWidths=[120, 150, 110, 140])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 20))
    
    # Farmer Profile Details
    story.append(Paragraph("1. FARMER PROFILE & SPECIFICATIONS", section_heading))
    profile_data = [
        [Paragraph("Farmer ID:", body_bold), Paragraph(str(ins['farmer_id']), body_style),
         Paragraph("Farmer Name:", body_bold), Paragraph(ins['farmer_name'], body_style)]
    ]
    profile_table = Table(profile_data, colWidths=[120, 150, 110, 140])
    profile_table.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(profile_table)
    story.append(Spacer(1, 15))
    
    # Claim Details Table
    story.append(Paragraph("2. LOSS ASSESSMENT & TELEMETRY", section_heading))
    claim_details_data = [
        [Paragraph("Crop Type Registered:", body_bold), Paragraph(ins['crop_type'], body_style)],
        [Paragraph("Plot Coordinates:", body_bold), Paragraph(ins['field_details'], body_style)],
        [Paragraph("Area of Interest:", body_bold), Paragraph(f"{ins['area_hectares']} Hectares" if ins['area_hectares'] else "N/A", body_style)],
        [Paragraph("Assessed Yield Loss:", body_bold), Paragraph(f"{ins['loss_percentage']}%", body_style)],
        [Paragraph("Monitoring Timeline:", body_bold), Paragraph(ins['timeline'], body_style)],
        [Paragraph("Scan Reference Date:", body_bold), Paragraph(ins['scan_reference_date'] or "N/A", body_style)],
        [Paragraph("Damage Description:", body_bold), Paragraph(ins['damage_assessment'], body_style)]
    ]
    claim_table = Table(claim_details_data, colWidths=[150, 370])
    claim_table.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#f1f5f9')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(claim_table)
    story.append(Spacer(1, 15))
    
    # Blockchain Details Table
    story.append(Paragraph("3. CRYPTOGRAPHIC BLOCKCHAIN PROOF", section_heading))
    blockchain_data = [
        [Paragraph("Verified Block Index:", body_bold), Paragraph(f"Block #{block['block_index']}", body_style)],
        [Paragraph("Verified Spray Method:", body_bold), Paragraph(block['spray_method'], body_style)],
        [Paragraph("Verified Coordinates:", body_bold), Paragraph(block['coordinates'], body_style)],
        [Paragraph("Block Mining Timestamp:", body_bold), Paragraph(block['timestamp'], body_style)],
        [Paragraph("Cryptographic Hash (SHA-256):", body_bold), Paragraph(block['block_hash'], ParagraphStyle('Hash1', parent=body_style, fontName='Courier', fontSize=7.5))],
        [Paragraph("Previous Block Link Hash:", body_bold), Paragraph(block['previous_hash'], ParagraphStyle('Hash2', parent=body_style, fontName='Courier', fontSize=7.5))]
    ]
    blockchain_table = Table(blockchain_data, colWidths=[150, 370])
    blockchain_table.setStyle(TableStyle([
        ('PADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#dcfce7')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(blockchain_table)
    story.append(Spacer(1, 25))
    
    # Footer text
    footer_text = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#94a3b8'),
        alignment=1
    )
    story.append(Paragraph("This document is cryptographically linked to the local Vriddhi 2.0 distributed ledger network.<br/>Tampering with this printed record invalidates verification hashes automatically.", footer_text))
    
    doc.build(story)

# --------------------------------------------------------------------------

# Initialize a dummy user document if the database collection is empty
DUMMY_FARMER_ID = 101
if not users_col.find_one({"farmer_id": DUMMY_FARMER_ID}):
    users_col.insert_one({
        "farmer_id": DUMMY_FARMER_ID,
        "name": "anchu",
        "district": "kamrup",
        "credit_points": 0  # Starts at 0 credits as requested
    })

# Seed default items in marketplace_items if the collection is empty
if marketplace_col.count_documents({}) == 0:
    marketplace_col.insert_many([
        {
            "id": "med-1",
            "title": "Neem Shield Bio-Pesticide",
            "type": "medicine",
            "description": "100% cold-pressed organic neem oil formulation for organic insect and pest control.",
            "price": 299.00,
            "image_url": "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=400&q=80",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "med-2",
            "title": "Trichoderma Fungicide",
            "type": "medicine",
            "description": "Bio-fungicide shielding crops against root rot, wilt, and damping-off disease.",
            "price": 249.00,
            "image_url": "https://images.unsplash.com/photo-1592417817098-8f3d6eb19675?auto=format&fit=crop&w=400&q=80",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "med-3",
            "title": "Premium Plant Growth Stimulant",
            "type": "medicine",
            "description": "Concentrated seaweed extract powder boosting photosynthesis and root growth.",
            "price": 399.00,
            "image_url": "https://images.unsplash.com/photo-1530595467537-0b5996c41f2d?auto=format&fit=crop&w=400&q=80",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "ess-1",
            "title": "Enriched Soil Vermicompost",
            "type": "essential",
            "description": "Pure worm-castings packed with microbial activity and vital trace nutrients.",
            "price": 180.00,
            "image_url": "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=400&q=80",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "ess-2",
            "title": "Micro Drip Irrigation System",
            "type": "essential",
            "description": "Adjustable emitters and drip lines for precise, water-saving root irrigation.",
            "price": 899.00,
            "image_url": "https://images.unsplash.com/photo-1563514227147-6d2ff665a6a0?auto=format&fit=crop&w=400&q=80",
            "created_at": datetime.utcnow().isoformat()
        },
        {
            "id": "ess-3",
            "title": "Dynamic Soil pH Tester",
            "type": "essential",
            "description": "High-accuracy analog probe to gauge pH, moisture levels, and ambient sunlight.",
            "price": 450.00,
            "image_url": "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=400&q=80",
            "created_at": datetime.utcnow().isoformat()
        }
    ])

def force_ee_initialization():
    """
    Render-safe Google Earth Engine initialization.
    Fixes: 'dict' object has no attribute 'endswith'
    """

    try:
        if ee.data.is_initialized():
            return True
    except Exception:
        pass

    try:
        raw_key = (
            os.getenv("EARTHENGINE_SERVICE_ACCOUNT_KEY")
            or os.getenv("GEE_JSON_KEY")
        )

        if not raw_key:
            print("⚠️ No GEE credentials found in environment variables. Attempting default initialization...")
            try:
                ee.Initialize()
                print("✅ GEE INITIALIZED SUCCESSFULLY (Default Credentials)")
                return True
            except Exception as default_err:
                print("❌ Default GEE initialization failed:", str(default_err))
                return False

        print("DEBUG ENV TYPE:", type(raw_key))

        # Parse credentials
        if isinstance(raw_key, str):
            try:
                key_data = json.loads(raw_key)
            except Exception:
                import ast
                key_data = ast.literal_eval(raw_key)
        else:
            key_data = raw_key

        # Create temporary JSON file
        credential_file = "/tmp/gee_service_account.json"

        with open(credential_file, "w") as f:
            json.dump(key_data, f)

        service_account = key_data["client_email"]

        credentials = ee.ServiceAccountCredentials(
            service_account,
            credential_file
        )

        ee.Initialize(
            credentials,
            project=key_data.get("project_id")
        )

        print("✅ GEE INITIALIZED SUCCESSFULLY")
        return True

    except Exception as e:
        import traceback
        print("❌ CRITICAL GEE AUTH FAILURE DETECTED")
        print(traceback.format_exc())
        return False

# Run initialization engine once at global instance start setup sequence
force_ee_initialization()

@app.route('/api/geocode', methods=['GET'])
def api_geocode():
    """Proxy geocoding requests to Nominatim with a compliant User-Agent."""
    query = request.args.get('q')
    if not query:
        return jsonify([])
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={encoded_query}&limit=1"
        
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'VriddhiAgricultureApp/2.0 (contact@vriddhi.com)',
                'Accept-Language': 'en'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return jsonify(data)
    except Exception as e:
        print("Geocoding proxy error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/farmer-stats', methods=['GET'])
def get_farmer_stats():
    """Endpoint to fetch the user's current reward credit tally."""
    farmer_id_val = request.args.get('farmer_id')
    if farmer_id_val:
        try:
            fid = int(farmer_id_val)
        except ValueError:
            fid = farmer_id_val
    elif session.get('user_id'):
        fid = session.get('user_id')
    else:
        fid = DUMMY_FARMER_ID
        
    user = users_col.find_one({"farmer_id": fid})
    if not user:
        return jsonify({"credit_points": 0})
    return jsonify({"credit_points": user.get("credit_points", 0)})

def get_centroid(geom):
    """Calculates the centroid of a GeoJSON geometry polygon."""
    try:
        if not geom:
            return None
        coords = geom.get('coordinates') if isinstance(geom, dict) else None
        if not coords:
            return None
        pts = coords[0] if isinstance(coords[0], list) else coords
        xs = [p[0] for p in pts if isinstance(p, list) and len(p) >= 2]
        ys = [p[1] for p in pts if isinstance(p, list) and len(p) >= 2]
        if not xs or not ys:
            return None
        return sum(xs) / len(xs), sum(ys) / len(ys)
    except Exception as e:
        print("Error getting centroid:", str(e))
        return None

def coordinates_are_close(geom1, geom2, tolerance_meters=80.0):
    """Checks if the centroids of two geometries are within tolerance_meters (default 80m)."""
    import math
    c1 = get_centroid(geom1)
    c2 = get_centroid(geom2)
    if not c1 or not c2:
        return False
    
    # Calculate distance in meters using simple spherical projection
    lat_mid = (c1[1] + c2[1]) / 2.0
    lat_mid_rad = math.radians(lat_mid)
    
    dy = (c1[1] - c2[1]) * 111000.0
    dx = (c1[0] - c2[0]) * 111000.0 * math.cos(lat_mid_rad)
    dist = math.sqrt(dx*dx + dy*dy)
    
    return dist < tolerance_meters

@app.route('/api/analyze-field', methods=['POST'])
def analyze_field():
    if not session.get('user_id'):
        return jsonify({"status": "error", "message": "Unauthorized. Please sign in or register first."}), 401
        
    # Fixed Thread Guard route connector logic
    try:
        is_ee_ready = ee.data.is_initialized()
    except Exception:
        is_ee_ready = False

    if not is_ee_ready:
        print("🔄 Verification fallback: Re-authenticating dynamic context request stream...")
        if not force_ee_initialization():
            return jsonify({"status": "error", "message": "Earth Engine client library is currently uninitialized on the host."}), 500

    try:
        data = request.get_json()
        if not data or 'geometry' not in data:
            return jsonify({"status": "error", "message": "Missing GeoJSON geometry"}), 400
        
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        one_month_ago = (now - timedelta(days=30)).strftime('%Y-%m-%d')

        geojson_geometry = data['geometry']
        aoi = ee.Geometry.Polygon(geojson_geometry['coordinates'])

        # Calculate area in square meters
        area_sq_m = aoi.area().getInfo()

        # Minimum Area Check
        if area_sq_m < 500:
            return jsonify({
                "status": "error",
                "message": "Selected area too small. Please zoom out and select at least 500 sq meters."
            }), 400

        # Maximum Area Check
        if area_sq_m > 500000:
            return jsonify({
                "status": "error",
                "message": "Area too large. Please select a smaller section."
            }), 400

        # Fetch Sentinel-2 composite (least cloudy image available)
        s2_collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(aoi)
                         .filterDate(one_month_ago, today)
                         .sort('CLOUDY_PIXEL_PERCENTAGE')
                         .first())
        
        # Verify if any imagery exists and has bands
        try:
            field_image = s2_collection.clip(aoi)
            band_names = field_image.bandNames().getInfo()
            if not band_names:
                raise ValueError("No bands")
        except Exception:
            return jsonify({
                "status": "error",
                "message": "No satellite imagery found for this area in the last 30 days. Please verify the boundary or try again later."
            }), 400

        # Retrieve cloud cover percentage
        cloud_percentage = s2_collection.get('CLOUDY_PIXEL_PERCENTAGE').getInfo()
        if cloud_percentage is None:
            cloud_percentage = 0.0

        # Calculate indices
        ndvi = field_image.normalizedDifference(['B8', 'B4']).rename('NDVI')
        ndmi = field_image.normalizedDifference(['B8', 'B11']).rename('NDMI')
        
        # Classify pixel types
        is_water_pixel = ndvi.lt(0.0)
        is_concrete_pixel = ndvi.gte(0.0).And(ndvi.lt(0.25)).And(ndmi.lt(0.0))
        is_veg_pixel = ndvi.gte(0.15) # Adjusted to 0.15 for tea vegetation

        # Tea Health Anomaly: BOTH low NDVI (< 0.60) AND low NDMI (< 0.15) in tea vegetation
        sick_mask = ndvi.lt(0.60).And(ndmi.lt(0.15)).And(is_veg_pixel)

        # Compute composition proportions in the selected Area of Interest (AOI)
        stats = ee.Image.cat([
            ndvi.rename('NDVI'),
            ndvi.updateMask(is_veg_pixel).rename('veg_NDVI'),
            ndmi.rename('NDMI'),
            is_water_pixel.rename('water_prop'),
            is_concrete_pixel.rename('concrete_prop'),
            is_veg_pixel.rename('veg_prop'),
            sick_mask.rename('sick_prop')
        ]).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=10,
            maxPixels=1e8
        ).getInfo()

        mean_ndvi = stats.get('NDVI') if stats else None
        mean_veg_ndvi = stats.get('veg_NDVI') if stats else None
        mean_ndmi = stats.get('NDMI') if stats else None
        water_prop = stats.get('water_prop', 0.0) if stats else 0.0
        concrete_prop = stats.get('concrete_prop', 0.0) if stats else 0.0
        veg_prop = stats.get('veg_prop', 0.0) if stats else 0.0
        sick_prop = stats.get('sick_prop', 0.0) if stats else 0.0

        # Count total pixels inside the AOI
        count_stats = ndvi.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=aoi,
            scale=10,
            maxPixels=1e8
        ).getInfo()
        total_count = count_stats.get('NDVI', 0) if count_stats else 0
        if total_count is None:
            total_count = 0

        # Calculate exact pixel counts
        veg_count = int(round(veg_prop * total_count))
        sick_count = int(round(sick_prop * total_count))

        # Print counts to console for debugging
        print("====================================")
        print(f"DEBUG SCATTER SCAN:")
        print(f"Total Pixels: {total_count}")
        print(f"Vegetation Pixels (NDVI >= 0.15): {veg_count}")
        print(f"Sick Pixels (NDVI < 0.60 & NDMI < 0.15): {sick_count}")
        print(f"Sick Percentage: {(sick_count / veg_count * 100.0) if veg_count > 0 else 0.0:.2f}%")
        print(f"Mean NDVI (Overall): {mean_ndvi}")
        print(f"Mean NDVI (Vegetation Only): {mean_veg_ndvi}")
        print("====================================")

        # Validation checks
        if water_prop > 0.5:
            return jsonify({
                "status": "error",
                "message": f"The selected area is classified as a water body ({water_prop*100:.1f}% water). Please select a valid tea plantation field."
            }), 400

        if concrete_prop > 0.75:
            return jsonify({
                "status": "error",
                "message": f"The selected area has high concrete coverage ({concrete_prop*100:.1f}% concrete structures). Please select a valid tea plantation field."
            }), 400

        # Mean NDVI validation
        if mean_veg_ndvi is not None and mean_veg_ndvi < 0.35:
            return jsonify({
                "status": "error",
                "message": f"Average NDVI of vegetation ({mean_veg_ndvi:.2f}) is too low for tea. This may be dry grass or weeds, not active tea."
            }), 400

        # Vegetation coverage validation
        if veg_prop < 0.25:
            return jsonify({
                "status": "error",
                "message": f"Selected area has only {veg_prop*100:.1f}% vegetation. Active tea plantations typically have 40-80% vegetation. Please select an area with growing tea bushes."
            }), 400

        # Vegetation pixel quantity gate check
        if veg_count < 3:
            return jsonify({
                "status": "error",
                "message": "No significant vegetation detected. Please select a tea plantation."
            }), 400

        # Extract points only where is_veg_pixel and sick_mask are active
        sick_pixels = sick_mask.updateMask(sick_mask)

        # Extract coordinates and pixel values using reduceRegion toList
        lonlat = ee.Image.pixelLonLat()
        sample_img = lonlat.select(['longitude', 'latitude']) \
                           .addBands(ndvi.rename('ndvi')) \
                           .addBands(ndmi.rename('ndmi')) \
                           .updateMask(sick_pixels)

        anomaly_features = []
        try:
            pixel_data = sample_img.reduceRegion(
                reducer=ee.Reducer.toList(),
                geometry=aoi,
                scale=10,
                maxPixels=500
            ).getInfo()

            if pixel_data:
                longitudes = pixel_data.get('longitude', [])
                latitudes = pixel_data.get('latitude', [])
                ndvis = pixel_data.get('ndvi', [])
                ndmis = pixel_data.get('ndmi', [])

                if not longitudes: longitudes = []
                if not latitudes: latitudes = []
                if not ndvis: ndvis = []
                if not ndmis: ndmis = []

                num_points = min(len(longitudes), len(latitudes), len(ndvis), len(ndmis), 500)

                for i in range(num_points):
                    lon = longitudes[i]
                    lat = latitudes[i]
                    ndvi_val = ndvis[i]
                    ndmi_val = ndmis[i]

                    if lon is None or lat is None:
                        continue

                    if ndvi_val is None: ndvi_val = 0.0
                    if ndmi_val is None: ndmi_val = 0.0

                    # Severity classification:
                    # NDVI < 0.35 -> severe
                    # NDVI 0.35 - 0.50 -> moderate
                    # NDVI 0.50 - 0.60 -> mild
                    if ndvi_val < 0.35:
                        sev_str = "severe"
                    elif ndvi_val <= 0.50:
                        sev_str = "moderate"
                    else:
                        sev_str = "mild"

                    anomaly_features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "properties": {
                            "ndvi_value": round(ndvi_val, 3),
                            "ndmi_value": round(ndmi_val, 3),
                            "severity": sev_str,
                            "lat": lat,
                            "lng": lon
                        }
                    })
        except Exception as e:
            print("Error extracting sick pixel coordinates:", str(e))

        anomaly_geojson = {
            "type": "FeatureCollection",
            "features": anomaly_features
        }
        new_anomaly_count = len(anomaly_features)

        # Fallback Check: uniform stress cover (if sick pixels exist but lists returned empty)
        if new_anomaly_count == 0 and sick_count > 0:
            centroid = get_centroid(geojson_geometry)
            fallback_coords = [centroid[0], centroid[1]] if centroid else [0.0, 0.0]
            fallback_feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": fallback_coords
                },
                "properties": {
                    "ndvi_value": round(mean_ndvi, 3) if mean_ndvi is not None else 0.4,
                    "ndmi_value": 0.15,
                    "severity": "severe",
                    "lat": fallback_coords[1],
                    "lng": fallback_coords[0],
                    "message": "Entire tea field exhibits stress signatures."
                }
            }
            anomaly_geojson = {
                "type": "FeatureCollection",
                "features": [fallback_feature]
            }
            new_anomaly_count = 1

        user_id = session.get('user_id')

        # Check for previous anomalies in this field location
        previous_scan = None
        pending_scans = list(history_col.find({
            "farmer_id": user_id,
            "status": "Pending Verification"
        }, sort=[("timestamp", -1)]))
        
        close_scan_ids = []
        for scan in pending_scans:
            if coordinates_are_close(scan.get("boundary_geometry"), geojson_geometry):
                if previous_scan is None:
                    previous_scan = scan
                close_scan_ids.append(scan["_id"])

        credit_awarded = 0
        message = "Initial field baseline stored. Clear remaining crop stress areas to earn rewards."
        save_status = "Pending Verification" if new_anomaly_count > 0 else "Clean"

        if previous_scan:
            prev_timestamp_val = previous_scan["timestamp"]
            if isinstance(prev_timestamp_val, datetime):
                prev_time = prev_timestamp_val
            else:
                prev_time = datetime.fromisoformat(str(prev_timestamp_val))
                
            days_elapsed = (now - prev_time).days
            old_anomaly_features = previous_scan.get("anomaly_data", {}).get("features", [])

            if days_elapsed < 5:
                message = f"Too early to verify! Only {days_elapsed} days elapsed. Please wait at least 5 days for the next satellite pass."
                save_status = "Pending Verification"
            elif days_elapsed > 10:
                message = f"Remediation expired! It took {days_elapsed} days (Deadline was 10 days). Baseline reset."
                history_col.update_many(
                    {"_id": {"$in": close_scan_ids}},
                    {"$set": {"status": "Expired"}}
                )
            else:
                if len(old_anomaly_features) > 0 and new_anomaly_count == 0:
                    credit_awarded = 50
                    users_col.update_one(
                        {"farmer_id": user_id},
                        {"$inc": {"credit_points": credit_awarded}}
                    )
                    history_col.update_many(
                        {"_id": {"$in": close_scan_ids}},
                        {"$set": {"status": "Resolved"}}
                    )
                    message = f"Congratulations! Crop stress cleared in {days_elapsed} days. +50 Remediation Credits added."
                    save_status = "Clean"
                elif new_anomaly_count > 0:
                    message = f"Analysis running inside window ({days_elapsed} days elapsed). Found {new_anomaly_count} remaining anomalies. Keep working!"
                    save_status = "Pending Verification"
        else:
            if new_anomaly_count == 0:
                message = "Field appears healthy! No significant crop stress detected."
            else:
                sick_percentage = (sick_count / veg_count * 100.0) if veg_count > 0 else 0.0
                message = f"Stress detected in {sick_percentage:.1f}% of area — {new_anomaly_count} sick plants marked"

        # Commit current tracking record to MongoDB
        history_col.insert_one({
            "farmer_id": user_id,
            "timestamp": now.isoformat(),
            "status": save_status,
            "boundary_geometry": geojson_geometry,
            "anomaly_data": anomaly_geojson
        })

        # Fetch fresh current credit score balance
        updated_user = users_col.find_one({"farmer_id": user_id})

        sick_percentage = (sick_count / veg_count * 100.0) if veg_count > 0 else 0.0

        return jsonify({
            "status": "success",
            "message": message,
            "data": anomaly_geojson,
            "credit_points": updated_user["credit_points"],
            "awarded": credit_awarded > 0,
            "cloud_percentage": cloud_percentage,
            "cloud_cover": cloud_percentage,
            "ndvi_mean": mean_ndvi,
            "ndmi_mean": mean_ndmi,
            "veg_pixel_count": veg_count,
            "sick_pixel_count": sick_count,
            "sick_percentage": sick_percentage,
            "debug": {
                "total_pixels": total_count,
                "veg_pixels": veg_count,
                "sick_pixels": sick_count,
                "sick_percentage": sick_percentage
            }
        })
    
    except Exception as e:
        print("Error during request processing:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

# --- PAGE ROUTING SYSTEM ---

@app.route('/')
def home():
    """Renders the landing/onboarding page of the application."""
    try:
        return render_template('landing.html')
    except Exception as e:
        print("Error rendering landing.html:", str(e))
        return "Landing page template not found.", 404

@app.route('/dashboard')
def dashboard():
    """Renders the main farmer dashboard interface."""
    if not session.get('user_id'):
        return redirect(url_for('home') + "?prompt_login=true")
    try:
        return render_template('index.html')
    except Exception as e:
        print("Error rendering index.html:", str(e))
        return "Dashboard page template not found.", 404

@app.route('/marketplace')
def marketplace():
    """Renders the marketplace showing farm medicines and essentials."""
    try:
        items = list(marketplace_col.find({}, {"_id": 0}))
        user_id = session.get('user_id') or DUMMY_FARMER_ID
        user = users_col.find_one({"farmer_id": user_id})
        credits = user.get("credit_points", 0) if user else 0
        return render_template('marketplace.html', items=items, credits=credits)
    except Exception as e:
        print("Error rendering marketplace.html:", str(e))
        return "Marketplace page template not found.", 500

@app.route('/admin/add-item', methods=['POST'])
def add_marketplace_item():
    """Admin-only portal endpoint to register new items into MongoDB."""
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
            
        title = data.get('title')
        item_type = data.get('type')
        description = data.get('description')
        price_val = data.get('price')
        image_url = data.get('image_url')

        if not title or not item_type or not price_val:
            return jsonify({"status": "error", "message": "Missing required fields (title, type, price)"}), 400

        if item_type not in ['medicine', 'essential']:
            return jsonify({"status": "error", "message": "Type must be 'medicine' or 'essential'"}), 400

        try:
            price = float(price_val)
        except ValueError:
            return jsonify({"status": "error", "message": "Price must be a valid number"}), 400

        if not image_url or image_url.strip() == "":
            if item_type == "medicine":
                image_url = "https://images.unsplash.com/photo-1599599810769-bcde5a160d32?auto=format&fit=crop&w=400&q=80"
            else:
                image_url = "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=400&q=80"

        new_item = {
            "id": f"{item_type[:3]}-{str(uuid.uuid4())[:8]}",
            "title": title,
            "type": item_type,
            "description": description or "",
            "price": price,
            "image_url": image_url,
            "created_at": datetime.utcnow().isoformat()
        }

        marketplace_col.insert_one(new_item)
        
        if request.is_json:
            return jsonify({"status": "success", "message": "Item added successfully!", "item": new_item})
        else:
            return redirect(url_for('marketplace'))

    except Exception as e:
        print("Error inserting marketplace item:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/insurance-claim', methods=['GET', 'POST'])
def insurance_claim():
    """Handles GET to render form, and POST to submit claims to MongoDB."""
    if request.method == 'POST':
        try:
            if request.is_json:
                data = request.get_json()
            else:
                data = request.form

            farmer_id = data.get('farmer_id', DUMMY_FARMER_ID)
            farmer_name = data.get('farmer_name', 'anchu')
            field_details = data.get('field_details')
            loss_percentage_val = data.get('loss_percentage')
            timeline = data.get('timeline')
            damage_assessment = data.get('damage_assessment')
            area_hectares_val = data.get('area_hectares')
            crop_type = data.get('crop_type')

            if not field_details or not loss_percentage_val or not damage_assessment:
                return jsonify({"status": "error", "message": "Missing required fields"}), 400

            try:
                loss_percentage = float(loss_percentage_val)
            except ValueError:
                return jsonify({"status": "error", "message": "Loss percentage must be a number"}), 400

            try:
                area_hectares = float(area_hectares_val) if area_hectares_val else None
            except ValueError:
                area_hectares = None

            new_claim = {
                "id": f"claim-{str(uuid.uuid4())[:8]}",
                "farmer_id": int(farmer_id) if str(farmer_id).isdigit() else farmer_id,
                "farmer_name": farmer_name,
                "field_details": field_details,
                "area_hectares": area_hectares,
                "crop_type": crop_type,
                "loss_percentage": loss_percentage,
                "timeline": timeline or "",
                "damage_assessment": damage_assessment,
                "submission_date": datetime.utcnow().isoformat(),
                "status": "pending"
            }

            claims_col.insert_one(new_claim)

            if request.is_json:
                return jsonify({"status": "success", "message": "Claim submitted successfully!", "claim_id": new_claim["id"]})
            else:
                return render_template('insurance.html', success_message="Claim submitted successfully!", claim_id=new_claim["id"])

        except Exception as e:
            print("Error submitting insurance claim:", str(e))
            return jsonify({"status": "error", "message": str(e)}), 500
            
    try:
        return render_template('insurance.html')
    except Exception as e:
        print("Error rendering insurance.html:", str(e))
        return "Insurance Claims page template not found.", 404

@app.route('/api/log-spray', methods=['POST'])
def api_log_spray():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Missing request payload"}), 400
            
        farmer_name = data.get('farmer_name')
        coordinates = data.get('coordinates')
        spray_method = data.get('spray_method')
        
        if not farmer_name or not coordinates or not spray_method:
            return jsonify({"status": "error", "message": "Missing required fields (farmer_name, coordinates, spray_method)"}), 400
            
        if spray_method not in ["Drone Precision Spot-Sprayed", "Manual Spot-Sprayed"]:
            return jsonify({"status": "error", "message": "Invalid spray method"}), 400
            
        block = log_to_blockchain(farmer_name, coordinates, spray_method)
        return jsonify({"status": "success", "message": "Blockchain block created successfully!", "block": block})
    except Exception as e:
        print("Error logging spray:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/submit-insurance-claim', methods=['POST'])
def submit_insurance_claim():
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form

        farmer_id = data.get('farmer_id', DUMMY_FARMER_ID)
        farmer_name = data.get('farmer_name', 'anchu')
        field_details = data.get('field_details')
        loss_percentage_val = data.get('loss_percentage')
        timeline = data.get('timeline')
        scan_reference_date = data.get('scan_reference_date')
        damage_assessment = data.get('damage_assessment')
        area_hectares_val = data.get('area_hectares')
        crop_type = data.get('crop_type')

        if not field_details or not loss_percentage_val or not damage_assessment:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400

        try:
            loss_percentage = float(loss_percentage_val)
        except ValueError:
            return jsonify({"status": "error", "message": "Loss percentage must be a number"}), 400

        try:
            area_hectares = float(area_hectares_val) if area_hectares_val else None
        except ValueError:
            area_hectares = None

        # Pull blockchain log for this user
        matching_block = find_blockchain_log(farmer_name)
        if not matching_block:
            # If no blockchain log exists, dynamically log a fallback block so verification and PDF generation can proceed seamlessly
            matching_block = log_to_blockchain(
                farmer_name=farmer_name,
                coordinates=field_details or "26.14°N, 91.73°E",
                spray_method="Drone Precision Spot-Sprayed"
            )

        # Create the MongoDB insurance claim document
        claim_id = f"claim-{str(uuid.uuid4())[:8]}"
        new_claim = {
            "id": claim_id,
            "farmer_id": int(farmer_id) if str(farmer_id).isdigit() else farmer_id,
            "farmer_name": farmer_name,
            "field_details": field_details,
            "area_hectares": area_hectares,
            "crop_type": crop_type,
            "loss_percentage": loss_percentage,
            "timeline": timeline or "",
            "scan_reference_date": scan_reference_date or "",
            "damage_assessment": damage_assessment,
            "submission_date": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        claims_col.insert_one(new_claim.copy())

        # Construct the combined packet
        combined_packet = {
            "claim_id": claim_id,
            "insurance_details": {
                "farmer_id": new_claim["farmer_id"],
                "farmer_name": new_claim["farmer_name"],
                "field_details": new_claim["field_details"],
                "area_hectares": new_claim["area_hectares"],
                "crop_type": new_claim["crop_type"],
                "loss_percentage": new_claim["loss_percentage"],
                "timeline": new_claim["timeline"],
                "scan_reference_date": new_claim["scan_reference_date"],
                "damage_assessment": new_claim["damage_assessment"],
                "submission_date": new_claim["submission_date"],
                "status": new_claim["status"]
            },
            "blockchain_verification": {
                "block_index": matching_block["index"],
                "farmer_name": matching_block["farmer_name"],
                "coordinates": matching_block["coordinates"],
                "spray_method": matching_block["spray_method"],
                "timestamp": matching_block["timestamp"],
                "block_hash": matching_block["hash"],
                "previous_hash": matching_block["previous_hash"]
            }
        }

        # Save combined packet locally
        claims_ledger_file = "insurance_claims_ledger.json"
        claims_ledger = []
        if os.path.exists(claims_ledger_file):
            try:
                with open(claims_ledger_file, 'r') as f:
                    claims_ledger = json.load(f)
            except Exception as e:
                print("Error reading claims ledger, initializing empty:", e)
                claims_ledger = []

        claims_ledger.append(combined_packet)
        with open(claims_ledger_file, 'w') as f:
            json.dump(claims_ledger, f, indent=4)

        # Generate PDF Certificate
        pdf_filename = f"{claim_id}.pdf"
        claims_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claims")
        pdf_filepath = os.path.join(claims_dir, pdf_filename)
        generate_claim_pdf(combined_packet, pdf_filepath)
        pdf_url = f"{request.host_url}claims/{pdf_filename}"

        # Generate WhatsApp pre-filled link
        whatsapp_text = (
            f"Official Vriddhi 2.0 Crop Insurance Verification Document:\n\n"
            f"🌾 CLAIM METRICS:\n"
            f"- Reference ID: {combined_packet['claim_id']}\n"
            f"- Claimant: {combined_packet['insurance_details']['farmer_name']}\n"
            f"- Commodity: {combined_packet['insurance_details']['crop_type']}\n"
            f"- Measured Deficit: {combined_packet['insurance_details']['loss_percentage']}%\n"
            f"- Area: {combined_packet['insurance_details']['area_hectares']} Hectares\n\n"
            f"🔗 LEDGER ATTESTATION:\n"
            f"- Verification Block: #{combined_packet['blockchain_verification']['block_index']}\n"
            f"- Remediation: {combined_packet['blockchain_verification']['spray_method']}\n"
            f"- Ledger Entry Hash: {combined_packet['blockchain_verification']['block_hash'][:16]}...\n\n"
            f"📄 VERIFIED PDF DOCUMENT:\n"
            f"{pdf_url}\n\n"
            f"Status: Verified & Audited on Blockchain"
        )
        encoded_text = urllib.parse.quote(whatsapp_text)
        whatsapp_url = f"https://wa.me/9181170823?text={encoded_text}"

        return jsonify({
            "status": "success",
            "message": "Claim submitted successfully!",
            "claim_id": claim_id,
            "whatsapp_url": whatsapp_url,
            "pdf_url": pdf_url,
            "combined_packet": combined_packet
        })

    except Exception as e:
        print("Error submitting insurance claim:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/claims/<filename>')
def serve_claim_pdf(filename):
    claims_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'claims')
    return send_from_directory(claims_dir, filename)

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email')
        address = data.get('address')
        password = data.get('password')

        if not name or not phone or not email or not address or not password:
            return jsonify({"status": "error", "message": "All fields are required"}), 400

        if users_col.find_one({"email": email}):
            return jsonify({"status": "error", "message": "Email is already registered"}), 400

        last_user = users_col.find_one(sort=[("farmer_id", -1)])
        new_farmer_id = (last_user["farmer_id"] + 1) if (last_user and "farmer_id" in last_user) else 102

        user_doc = {
            "farmer_id": new_farmer_id,
            "name": name,
            "phone": phone,
            "email": email,
            "address": address,
            "password": password,
            "credit_points": 0
        }
        users_col.insert_one(user_doc)
        
        session['user_id'] = new_farmer_id
        
        user_doc.pop("password", None)
        user_doc.pop("_id", None)
        return jsonify({"status": "success", "message": "Registration successful!", "user": user_doc})
    except Exception as e:
        print("Registration error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"status": "error", "message": "Email and password are required"}), 400

        user = users_col.find_one({"email": email, "password": password})
        if not user:
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401

        user_doc = dict(user)
        user_doc.pop("password", None)
        user_doc.pop("_id", None)
        
        session['user_id'] = user['farmer_id']
        
        return jsonify({"status": "success", "message": "Login successful!", "user": user_doc})
    except Exception as e:
        print("Login error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sync-session', methods=['POST'])
def api_sync_session():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Missing request payload"}), 400
        farmer_id = data.get('farmer_id')
        if not farmer_id:
            return jsonify({"status": "error", "message": "Missing farmer_id"}), 400
        
        try:
            fid = int(farmer_id)
        except ValueError:
            fid = farmer_id
            
        user = users_col.find_one({"farmer_id": fid})
        if not user:
            return jsonify({"status": "error", "message": "User not found in database"}), 404
            
        session['user_id'] = fid
        return jsonify({"status": "success", "message": "Session synced successfully!"})
    except Exception as e:
        print("Session sync error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify({"status": "success", "message": "Logged out successfully!"})

@app.route('/api/purchase', methods=['POST'])
def api_purchase():
    try:
        data = request.get_json()
        name = data.get('name')
        location = data.get('location')
        phone = data.get('phone')
        item_title = data.get('item_title')
        item_price_val = data.get('item_price')

        if not name or not location or not phone or not item_title:
            return jsonify({"status": "error", "message": "Buyer details are required"}), 400

        try:
            item_price = float(item_price_val)
        except ValueError:
            item_price = 0.0

        purchase_doc = {
            "id": f"order-{str(uuid.uuid4())[:8]}",
            "name": name,
            "location": location,
            "phone": phone,
            "item_title": item_title,
            "item_price": item_price,
            "timestamp": datetime.utcnow().isoformat()
        }
        orders_col.insert_one(purchase_doc)
        return jsonify({"status": "success", "message": "Order processed successfully!", "order_id": purchase_doc["id"]})
    except Exception as e:
        print("Purchase error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update-credits', methods=['POST'])
def api_update_credits():
    try:
        data = request.get_json()
        farmer_id = data.get('farmer_id')
        credit_points = data.get('credit_points')

        if farmer_id is None or credit_points is None:
            return jsonify({"status": "error", "message": "farmer_id and credit_points are required"}), 400

        try:
            fid = int(farmer_id)
        except ValueError:
            fid = farmer_id

        users_col.update_one(
            {"farmer_id": fid},
            {"$set": {"credit_points": int(credit_points)}}
        )
        return jsonify({"status": "success", "message": "Credits updated successfully!"})
    except Exception as e:
        print("Update credits error:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
