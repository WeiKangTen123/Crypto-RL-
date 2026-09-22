from flask import Flask, request, jsonify

app = Flask(__name__)

# In-memory store for features
features_db = []

@app.route('/api/v1/features', methods=['POST'])
def create_feature():
    # We expect raw markdown string
    content = request.get_data(as_text=True)
    
    if not content:
        return jsonify({"error": "Empty payload"}), 400

    # Store it in our "database"
    new_feature = {
        "id": len(features_db) + 1,
        "content": content
    }
    features_db.append(new_feature)
    
    print(f"✅ Received new feature! Total features: {len(features_db)}")
    return jsonify({"message": "Feature added successfully", "feature_id": new_feature["id"]}), 201

@app.route('/api/v1/features', methods=['GET'])
def get_features():
    return jsonify({
        "total": len(features_db),
        "features": features_db
    }), 200

if __name__ == '__main__':
    print("🚀 Starting mock Feature Hub server on http://localhost:8000 ...")
    app.run(host='0.0.0.0', port=8000)
