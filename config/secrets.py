# New file: config/secrets.py
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
YOUDAO_API_KEY = os.getenv('YOUDAO_API_KEY')
YOUDAO_APP_SECRET = os.getenv('YOUDAO_APP_SECRET')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# ... etc

