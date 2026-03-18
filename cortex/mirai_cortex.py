import time
import subprocess
import json
import sys
from system_prompt import MIRAI_SYSTEM_PROMPT

class MiraiBrain:
    """
    Connects to the local OpenClaw Gateway to utilize the selected model.
    By default, uses Claude 3 Opus via OAuth for state-of-the-art free reasoning.
    """
    def __init__(self, model="anthropic/claude-opus-4-6"):
        self.model = model
        print(f"[MiraiBrain] Initialized Neural Link to OpenClaw Gateway via {self.model}")

    def think(self, prompt: str) -> str:
        """
        Sends a prompt to the selected model via the OpenClaw CLI.
        """
        try:
            result = subprocess.run(
                [
                    "openclaw", "agent", 
                    "--message", prompt, 
                    "--model", self.model,
                    "--thinking", "high" # Emulate deep reasoning 
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] Cortex Disconnect: {e.stderr}")
            return '{"action": "standby", "reason": "Brain disconnected"}'

class MiraiCortex:
    """
    The main autonomous loop (The Heartbeat).
    Orchestrates the Browser (Hands), the Brain (LLM), and the Subconscious (MiroFish).
    """
    def __init__(self, model):
        self.brain = MiraiBrain(model=model)
        self.objective = "Initialize systems, map local environment, and await user directives via WhatsApp."
        
    def execute_action(self, action_json: str):
        """
        Parses the JSON response from the LLM and takes action.
        """
        try:
            # Strip markdown formatting if the model returns a markdown block
            if action_json.startswith("```json"):
                action_json = action_json[7:-3].strip()
            elif action_json.startswith("```"):
                action_json = action_json[3:-3].strip()
                
            action_data = json.loads(action_json)
            action_type = action_data.get("action")
            
            if action_type == "browser_navigate":
                # TODO: Implement robust browser-use integration (fixing the websocket leak)
                print(f"[HANDS] Navigating to: {action_data.get('url')}")
            elif action_type == "terminal_command":
                print(f"[HANDS] Executing command: {action_data.get('command')}")
            elif action_type == "swarm_predict":
                # TODO: Implement localized MiroFish integration
                print(f"[SUBCONSCIOUS] Waking swarm to predict: {action_data.get('scenario')}")
            elif action_type == "message_human":
                # Route this through OpenClaw Gateway to push a message to the human
                message_text = action_data.get('text', '')
                print(f"[COMMS] Messaging Human: {message_text}")
                try:
                    subprocess.run(
                        [
                            "openclaw", "agent", 
                            "--message", message_text,
                            "--to", "WhatsApp" # Placeholder, OpenClaw routes to default channel
                        ],
                        capture_output=True,
                        check=True
                    )
                except subprocess.CalledProcessError as e:
                    print(f"[ERROR] Failed to message human via OpenClaw: {e.stderr}")
            elif action_type == "standby":
                print("[SYSTEM] Standing by...")
            else:
                print(f"[SYSTEM] Unknown action: {action_type}")
                
        except json.JSONDecodeError:
            print(f"[WARNING] Cortex hallucinated non-JSON response: {action_json}")

    def run_forever(self):
        print("\n=============================================")
        print("          M I R A I   O N L I N E          ")
        print(f"     Architecture: {self.brain.model} Cortex     ")
        print("=============================================\n")
        
        while True:
            print(f"[*] Current Objective: {self.objective}")
            
            system_prompt = MIRAI_SYSTEM_PROMPT.format(objective=self.objective)
            
            print(f"[CORTEX] Querying {self.brain.model}...")
            thought = self.brain.think(system_prompt)
            
            print(f"[CORTEX] Decision Received: {thought}")
            self.execute_action(thought)
            
            # Adaptive Backoff / Heartbeat rhythm to prevent rate-limiting
            print("[SYSTEM] Cortical sleep cycle (10 seconds)...\n")
            time.sleep(10)

def choose_model():
    print("=============================================")
    print("       Initialize Mirai Neural Link          ")
    print("=============================================")
    print("Select the LLM to power the Cortex:")
    print("1. Claude 3 Opus via OAuth (Recommended - Best Logic, Zero Cost)")
    print("2. ChatGPT Plus via OAuth (Zero Cost)")
    print("3. Custom OpenClaw Model String")
    
    choice = input("\nEnter choice [1]: ").strip()
    
    if choice == "2":
        return "openai-codex:oauth"
    elif choice == "3":
        return input("Enter OpenClaw model string (e.g., openai/gpt-4o): ").strip()
    else:
        return "anthropic/claude-opus-4-6"

if __name__ == "__main__":
    selected_model = choose_model()
    mirai = MiraiCortex(model=selected_model)
    # UNLEASHED: Mirai begins autonomous heartbeat inside the sandbox
    mirai.run_forever()
    print("[SYSTEM] Mirai Cortex Scaffold Compiled Successfully.")
