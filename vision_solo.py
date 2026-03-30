import os
import json
import base64
import requests
import sys

# Path to Claude Code credentials
CRED_PATH = os.path.expanduser("~/.claude/.credentials.json")

def get_token():
    try:
        if not os.path.exists(CRED_PATH):
            print(f"Error: Credentials file not found at {CRED_PATH}")
            return None
        with open(CRED_PATH, 'r') as f:
            creds = json.load(f)
            return creds.get("claudeAiOauth", {}).get("accessToken")
    except Exception as e:
        print(f"Error reading credentials: {e}")
        return None

def analyze_image(image_path, prompt="Analyze this image."):
    token = get_token()
    if not token:
        print("Error: Could not find Claude Code access token. Please login using 'claude login'.")
        return

    try:
        with open(image_path, "rb") as image_file:
            data = image_file.read()
            encoded_string = base64.b64encode(data).decode('utf-8')
            
            # Simple mime-type detection based on extension
            ext = os.path.splitext(image_path)[1].lower()
            mime_type_map = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_type_map.get(ext, 'image/jpeg')
    except Exception as e:
        print(f"Error reading image file: {e}")
        return

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "anthropic-beta": "oauth-2025-04-20", # Required for Claude Code OAuth tokens
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }

    # Using the latest Opus 4.6 model found in the binary
    payload = {
        "model": "claude-opus-4-6",
        "max_tokens": 4096,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": encoded_string
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    print(f"Sending request to Claude Opus 4.6 ({mime_type})...")
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        print("\n--- Claude Opus 4.6 Analysis ---\n")
        print(result["content"][0]["text"])
    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code}")
        try:
            error_details = e.response.json()
            print(json.dumps(error_details, indent=2))
        except:
            print(e.response.text)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 vision_solo.py <image_path> [prompt]")
    else:
        img_path = sys.argv[1]
        user_prompt = sys.argv[2] if len(sys.argv) > 2 else "Analyze this image in detail."
        analyze_image(img_path, user_prompt)
