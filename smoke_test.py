from pathlib import Path
import os
from dotenv import load_dotenv
from google import genai

load_dotenv(Path(__file__).with_name('.env'))
api_key = os.getenv('GEMINI_API_KEY', '').strip()
model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash').strip()

if not api_key or api_key == 'replace_with_your_key_locally':
    raise SystemExit('Add your real key to local .env (do not share it).')

client = genai.Client(api_key=api_key)
response = client.models.generate_content(
    model=model,
    contents='Reply with exactly: Gemini connection OK'
)
print(response.text or 'No text response returned')
