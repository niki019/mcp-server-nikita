import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
CACHE_DIR = os.path.join(BASE_DIR, ".cache")
DB_PATH = os.path.join(BASE_DIR, "run_audit.db")

os.makedirs(CACHE_DIR, exist_ok=True)

def parse_yaml(text: str) -> dict:
    """A lightweight, zero-dependency YAML parser for nested configurations."""
    data = {}
    path = []
    
    for line in text.split('\n'):
        # Strip comments
        line_clean = re.sub(r'#.*', '', line)
        if not line_clean.strip():
            continue
            
        indent = len(line_clean) - len(line_clean.lstrip())
        content = line_clean.strip()
        
        # 2 spaces per indentation level
        level = indent // 2
        path = path[:level]
        
        if content.startswith('- '):
            val = content[2:].strip().strip('"').strip("'")
            parent = data
            for p in path[:-1]:
                parent = parent[p]
            list_key = path[-1]
            if list_key not in parent or not isinstance(parent[list_key], list):
                parent[list_key] = []
            parent[list_key].append(val)
        elif ':' in content:
            key, val = content.split(':', 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            
            parent = data
            for p in path:
                parent = parent[p]
                
            if val == "":
                parent[key] = {}
                path.append(key)
            else:
                # Convert types
                if val.lower() == 'true':
                    val = True
                elif val.lower() == 'false':
                    val = False
                else:
                    try:
                        if '.' in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass
                parent[key] = val
    return data

def load_yaml_file(file_path: str) -> dict:
    if not os.path.exists(file_path):
        return {}
    with open(file_path, 'r', encoding='utf-8') as f:
        return parse_yaml(f.read())

# Load configurations
pipeline_config = load_yaml_file(os.path.join(CONFIG_DIR, "pipeline.yaml"))

def get_product_config(product_name: str) -> dict:
    return load_yaml_file(os.path.join(CONFIG_DIR, "products", f"{product_name}.yaml"))

# Settings loaded from environment or config
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "<YOUR_GROQ_API_KEY>")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
