import os
import json
import time
import psycopg2
import vertexai
import numpy as np
from flask import Flask, request, jsonify, render_template
from vertexai.generative_models import GenerativeModel, Part, Image
from vertexai.vision_models import MultiModalEmbeddingModel, Image as VertexImage
from vertexai.language_models import TextEmbeddingModel  
import base64
from io import BytesIO
import re

# --- CONFIGURATION ---
PROJECT_ID = "PROJECT_ID"
LOCATION = "us-central1"
DB_HOST = "IP_ADDRESS"
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASS = "**"

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Initialize Models
# Ingestion Model (Fast)
model_ingest = GenerativeModel("gemini-2.5-flash") 
# Reasoning/Agent Model (High Intelligence)
model_brain = GenerativeModel("gemini-2.5-flash") 
# Embedding Model
model_embedding = MultiModalEmbeddingModel.from_pretrained("multimodalembedding")

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- DATABASE HELPER ---
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    return conn

# --- CORE AI FUNCTIONS ---

def generate_embeddings(image_bytes, text_description=None):
    """
    Generates embeddings from raw bytes.
    """
    # VERTEX VISION: Can accept raw bytes directly
    image = VertexImage(image_bytes)
    
    # 1. Visual Embedding
    embeddings = model_embedding.get_embeddings(
        image=image,
        contextual_text=text_description 
    )
    visual_vector = embeddings.image_embedding
    
    # 2. Semantic Vector (Text)
    semantic_vector = [0.0] * 768
    if text_description:
        text_emb_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = text_emb_model.get_embeddings([text_description])
        semantic_vector = embeddings[0].values

    return visual_vector, semantic_vector


def analyze_garment(image_bytes, tactile_data):
    """
    Analyzes the garment using raw image bytes sent to Gemini.
    """
    roughness = tactile_data.get('roughness', 0)
    stiffness = tactile_data.get('stiffness', 0)
    
    prompt = f"""
    Analyze this garment image.
    I also have tactile sensor data from the fabric:
    - Roughness (0-1): {roughness}
    - Stiffness (0-1): {stiffness}

    Based on the image AND the tactile feel, provide a JSON response with:
    category, color, material_inference, season, vibe_description.
    """
    
    # GEMINI: Can accept raw bytes directly
    image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
    
    response = model_ingest.generate_content(
        [image_part, prompt],
        generation_config={"response_mime_type": "application/json"}
    )
    
    return json.loads(response.text)




# --- ROUTES ---

@app.route('/')
def index():
    conn = get_db_connection()
    cur = conn.cursor()
    # Fetch image_base64 instead of image_path
    cur.execute("SELECT id, image_base64, category, material_inference, season FROM wardrobe_items ORDER BY created_at DESC")
    items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', items=items)

# --- HARDWARE API ---
@app.route('/api/ingest', methods=['POST'])
def ingest_hardware_data():
    if 'image' not in request.files:
        return jsonify({"error": "No image part"}), 400
        
    file = request.files['image']
    tactile_raw = request.form.get('tactile_json', '{}')
    tactile_data = json.loads(tactile_raw)
    
    # 1. Read Bytes
    image_bytes = file.read()
    
    # 2. Convert to Base64 for Database Storage
    # We decode it to a UTF-8 string so it can be stored in a TEXT column
    base64_string = base64.b64encode(image_bytes).decode('utf-8')
    
    # 3. AI Processing (Pass raw bytes)
    metadata = analyze_garment(image_bytes, tactile_data)
    
    semantic_text = f"{metadata['vibe_description']} {metadata['material_inference']}"
    visual_vec, semantic_vec = generate_embeddings(image_bytes, semantic_text)
    
    # 4. Storage (AlloyDB)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wardrobe_items 
        (image_base64, tactile_roughness, tactile_stiffness, category, color, material_inference, brand, season, visual_embedding, semantic_embedding)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        base64_string, # Store the giant string here
        tactile_data.get('roughness'),
        tactile_data.get('stiffness'),
        metadata.get('category'),
        metadata.get('color'),
        metadata.get('material_inference'),
        "Generic",
        metadata.get('season'),
        str(visual_vec),
        str(semantic_vec)
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({"status": "success", "id": new_id, "analysis": metadata})

# --- AGENT ROUTES ---
@app.route('/api/agent/stylist', methods=['POST'])
def stylist_agent():
    """
    The Brain: Reasons about outfit choices based on context.
    Returns structured JSON with items and explanation.
    """
    data = request.json
    context = data.get('context') 
    
    # 1. Retrieve Candidate items using Semantic Search (Text-to-Text)
    # The semantic vector already captures the "vibe", so the search results are already relevant.
    text_emb_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
    embeddings = text_emb_model.get_embeddings([context])
    query_vec = embeddings[0].values
    
    conn = get_db_connection()
    cur = conn.cursor()
    # FIXED SQL: Removed 'vibe_description' column from SELECT
    cur.execute("""
        SELECT id, category, material_inference, color, season 
        FROM wardrobe_items 
        ORDER BY semantic_embedding <=> %s::vector 
        LIMIT 10
    """, (str(query_vec),))
    candidates = cur.fetchall()
    
    if not candidates:
         cur.close()
         conn.close()
         return jsonify({"explanation": "No suitable items found in wardrobe.", "items": []})

    # Format candidates for LLM
    candidate_str = ""
    for c in candidates:
        # FIXED PYTHON: Removed reference to non-existent vibe column (c[5])
        # We construct a factual description from available columns.
        candidate_str += f"- ID {c[0]}: {c[3]} {c[1]} (Material: {c[2]}, Season: {c[4]})\n"
    
    # 2. Agent Reasoning (Gemini Pro)
    prompt = f"""
    You are an expert fashion stylist. 
    User Context/Request: "{context}"
    
    Available Wardrobe Candidates (pre-filtered by relevance):
    {candidate_str}
    
    Task: Select the best 2-3 items from the list above to create a complete outfit for the context.
    
    Output Requirement: You MUST return ONLY raw JSON with this exact structure:
    {{
        "explanation": "A short, friendly stylist note explaining why these items work together for the context.",
        "item_ids": [id1, id2] 
    }}
    Do not use markdown block quotes. Just the raw JSON string.
    """
    
    try:
        response = model_brain.generate_content(
            prompt, 
            generation_config={"temperature": 0.3}
        )
        response_text = response.text.strip()
        
        # Clean up potential markdown formatting if Gemini adds it
        cleaned_text = re.sub(r"```json|```", "", response_text).strip()
        llm_data = json.loads(cleaned_text)
        
        selected_ids = llm_data.get("item_ids", [])
        explanation = llm_data.get("explanation", "Here is a suggestion.")

        if not selected_ids:
             raise ValueError("No items selected by LLM")

        # 3. Fetch full details for selected items
        # Need to cast IDs to int for safety
        clean_ids = tuple([int(x) for x in selected_ids])
        
        cur.execute(f"""
            SELECT id, image_base64, category, material_inference, color
            FROM wardrobe_items
            WHERE id IN %s
        """, (clean_ids,))
        
        final_items_raw = cur.fetchall()
        
        final_items = []
        for item in final_items_raw:
             final_items.append({
                 "id": item[0],
                 "image_base64": item[1],
                 "category": item[2],
                 "material": item[3],
                 "color": item[4]
             })

        cur.close()
        conn.close()
        
        return jsonify({"explanation": explanation, "items": final_items})

    except Exception as e:
        print(f"Error in stylist agent: {e}")
        if 'cur' in locals() and cur: cur.close()
        if 'conn' in locals() and conn: conn.close()
        # Return a structured error response that the frontend can handle gracefully
        return jsonify({"explanation": f"I had trouble creating an outfit right now. (Technical error: {str(e)})", "items": []})


@app.route('/api/agent/visual-match', methods=['POST'])
def visual_matcher_agent():
    """
    Visual Matcher (Complementary Mode): 
    Uses Gemini to find items that stylistically complete an outfit with the uploaded item.
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
        
    file = request.files['image']
    # Read bytes into memory. We need them twice: once for Gemini, once for DB (optional)
    input_image_bytes = file.read()

    # 1. Fetch Candidates from Database (Limit 25 for speed)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, category, color, material_inference, season, image_base64
        FROM wardrobe_items 
        ORDER BY created_at DESC
        LIMIT 25
    """)
    candidates_raw = cur.fetchall()
    cur.close()
    conn.close()

    if not candidates_raw:
         return jsonify({"matches": [], "reasoning": "Inventory is empty."})

    # Format candidates for LLM
    candidate_list_for_llm = []
    candidates_map = {} 
    for c in candidates_raw:
        item_summary = {
            "id": c[0], "category": c[1], "color": c[2], 
            "material": c[3], "season": c[4]
        }
        candidate_list_for_llm.append(item_summary)
        candidates_map[c[0]] = {
            "id": c[0], "category": c[1], "color": c[2], 
            "material": c[3], "image_base64": c[5]
        }

    candidates_str = json.dumps(candidate_list_for_llm, indent=2)

    # 2. The Brain: Ask Gemini to act as a stylist
    prompt_text = f"""
    You are an expert fashion stylist.
    
    Task: Create a complete outfit.
    1. Look at the input image provided (this is the item the user wants to wear).
    2. Look at the following inventory list from their closet:
    {candidates_str}

    3. Select exactly 3 distinct items from the inventory list that best complement the input image to create a stylish, complete outfit. 
    Exclude items that are too similar to the input (e.g., if input is shoes, don't pick other shoes).
     If input is a top, do not pick another top unless it is a blazer or a cardigan or part of an ensemble.

    If input is a bottom, do not pick another bottom unless it is part of an ensemble.

    Output Requirement:
    Return ONLY a raw JSON list of the 3 selected item IDs. Do not use markdown formatting.
    Example format: [15, 4, 22]
    """

    image_part = Part.from_data(data=input_image_bytes, mime_type="image/jpeg")
    
    try:
        response = model_brain.generate_content(
            [image_part, prompt_text],
            generation_config={"temperature": 0.4} 
        )
        response_text = response.text.strip()
        print(f"Gemini raw response: {response_text}") 

        # --- FIX: Robust JSON extraction ---
        # Instead of relying on regex to remove markdown, we find the 
        # first '[' and the last ']' to extract the array.
        try:
            start_index = response_text.find('[')
            end_index = response_text.rfind(']') + 1

            if start_index == -1 or end_index == 0:
                raise ValueError("No JSON brackets found in LLM response")

            json_str = response_text[start_index:end_index]
            selected_ids = json.loads(json_str)
        except Exception as json_err:
             print(f"Failed to extract/parse JSON from LLM response: {response_text}")
             raise json_err
        # ------------------------------------

        if not isinstance(selected_ids, list) or len(selected_ids) == 0:
             raise ValueError("LLM did not return a valid list of IDs")

        # 3. Retrieve full details for selected IDs
        final_matches = []
        for item_id in selected_ids:
            # Ensure ID is int and exists in our map
            try:
                sanitized_id = int(item_id)
                if sanitized_id in candidates_map:
                    final_matches.append(candidates_map[sanitized_id])
            except ValueError:
                 continue # Skip if LLM returned a non-integer ID
        
        return jsonify({"matches": final_matches[:3]})

    except Exception as e:
        print(f"Error in visual matcher agent: {e}")
        # Return empty list so frontend doesn't crash
        return jsonify({"matches": [], "error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    