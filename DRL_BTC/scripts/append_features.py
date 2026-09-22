import json

# Paths
dir_json = "/Users/weikangten/Desktop/Crypto-RL/DRL_BTC/docs/alpha_direction_kept.json"
vol_json = "/Users/weikangten/Desktop/Crypto-RL/DRL_BTC/docs/alpha_volatility_kept.json"
md_path = "/Users/weikangten/Desktop/Crypto-RL/DRL_BTC/docs/feature.MD"

def extract_features(data):
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        for key in ["kept", "kept_features", "features", "columns"]:
            if key in data and isinstance(data[key], list):
                return data[key]
    return []

# Load features
try:
    with open(dir_json, "r") as f:
        dir_data = json.load(f)
        dir_features = extract_features(dir_data)
except Exception:
    dir_features = []

try:
    with open(vol_json, "r") as f:
        vol_data = json.load(f)
        vol_features = extract_features(vol_data)
except Exception:
    vol_features = []

# Append to MD
with open(md_path, "a") as f:
    f.write("\n\n# Engineered ML Features (from ytee)\n")
    
    if dir_features:
        f.write(f"\n## 5. Alpha Direction Features ({len(dir_features)} features kept)\n")
        f.write("> These features were selected for predicting directional price movement after removing collinearity.\n\n")
        
        chunked = [dir_features[i:i+10] for i in range(0, len(dir_features), 10)]
        for chunk in chunked:
            f.write("`" + "`, `".join(chunk) + "`<br>\n")
            
    if vol_features:
        f.write(f"\n## 6. Alpha Volatility Features ({len(vol_features)} features kept)\n")
        f.write("> These features were selected for predicting market volatility.\n\n")
        
        chunked = [vol_features[i:i+10] for i in range(0, len(vol_features), 10)]
        for chunk in chunked:
            f.write("`" + "`, `".join(chunk) + "`<br>\n")

print("Appended features to MD successfully!")
