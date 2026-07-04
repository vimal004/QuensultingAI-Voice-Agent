import os
import sys
from dotenv import load_dotenv
from retell import Retell

def main():
    # Load environment variables
    load_dotenv()
    
    api_key = os.getenv("RETELL_API_KEY")
    agent_id = os.getenv("RETELL_AGENT_ID")
    
    # Render webhook URL
    webhook_url = "https://quensultingai-voice-agent.onrender.com/webhook/retell"
    
    if not api_key:
        print("Error: RETELL_API_KEY is not set in your .env file.", file=sys.stderr)
        sys.exit(1)
        
    if not agent_id:
        print("Error: RETELL_AGENT_ID is not set in your .env file.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Initializing Retell client with API Key...")
    client = Retell(api_key=api_key)
    
    print(f"Updating Agent '{agent_id}' webhook settings...")
    try:
        updated_agent = client.agent.update(
            agent_id=agent_id,
            webhook_url=webhook_url,
            # Explicitly subscribe to both call_started and call_analyzed (and call_ended)
            webhook_events=["call_started", "call_ended", "call_analyzed"]
        )
        print("\nSuccess! Webhook configuration successfully updated on Retell AI.")
        print(f"Agent ID: {updated_agent.agent_id}")
        print(f"Webhook URL: {updated_agent.webhook_url}")
        print(f"Subscribed Webhook Events: {updated_agent.webhook_events}")
    except Exception as e:
        print(f"\nError updating webhook config via Retell API: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
