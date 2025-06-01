import os
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
TAVUS_API_KEY = "ff5322363aed4974bfa4b5feb2891c3f"
PPLX_API_KEY = "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"
LLAMA_API_KEY = "LLM|1371372244155896|9NA7LMJ_zjvXVm8PBzrVio7nK3c"

# Model Configuration
SEARCH_MODEL = "sonar"  # For product search via Perplexity
INFERENCE_MODEL = "llama-4-maverick-17b-128e-instruct-fp8"  # For later inference

# Tavus Configuration
PERSONA_ID = "p9a95912"  # Demo Persona ID
REPLICA_ID = "r79e1c033f"  # Demo Persona's replica ID

# API Endpoints
TAVUS_CONVERSATION_URL = "https://tavusapi.com/v2/conversations"
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"
LLAMA_URL = "https://api.llama.ai/chat/completions"

class SearchAgent:
    def __init__(self):
        if not TAVUS_API_KEY:
            raise ValueError("Tavus API key is required")
        if not PPLX_API_KEY:
            raise ValueError("Perplexity API key is required")
            
        self.headers = {
            "x-api-key": TAVUS_API_KEY,
            "Content-Type": "application/json"
        }
        self.conversation_id = None
        self.conversation_url = None
        
        # Validate API keys on initialization
        self._validate_api_keys()

    def _validate_api_keys(self):
        """Validate both Tavus and Perplexity API keys"""
        # Validate Tavus API key
        try:
            response = requests.get(
                "https://tavusapi.com/v2/personas",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 401:
                raise ValueError("Invalid Tavus API key: Unauthorized")
            elif response.status_code == 403:
                raise ValueError("Invalid Tavus API key: Forbidden")
            elif response.status_code != 200:
                print(f"Warning: Unexpected status code {response.status_code}")
                print("Response:", response.text)
            
            print("✅ Tavus API key validated successfully")
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to connect to Tavus API: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error validating Tavus API key: {e}")

        # Validate Perplexity API key
        try:
            headers = {
                "Authorization": f"Bearer {PPLX_API_KEY}",
                "Content-Type": "application/json"
            }
            response = requests.post(
                PERPLEXITY_URL,
                json={
                    "model": SEARCH_MODEL,
                    "messages": [{"role": "user", "content": "test"}]
                },
                headers=headers,
                timeout=10
            )
            if response.status_code == 401:
                raise ValueError("Invalid Perplexity API key: Unauthorized")
            print("✅ Perplexity API key validated successfully")
            
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to connect to Perplexity API: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error validating Perplexity API key: {e}")

    def search_product(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """Search for products using Perplexity API with llama-3-sonar-large-32k-online"""
        headers = {
            "Authorization": f"Bearer {PPLX_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Construct a detailed search prompt
        search_prompt = f"""
        Search for products matching this query: {query}
        Return results in this format:
        - Product Name
        - Price
        - Description
        - Where to buy
        - Availability
        
        Limit to {max_results} results.
        Focus on current prices and availability.
        """
        
        body = {
            "model": SEARCH_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a product search assistant. Return detailed product information in a structured format."
                },
                {
                    "role": "user",
                    "content": search_prompt
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.1,
            "top_p": 0.9,
            "stream": False
        }
        
        try:
            print(f"\nSearching for: {query}")
            response = requests.post(
                PERPLEXITY_URL,
                json=body,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            return self._process_search_results(response.json())
            
        except Exception as e:
            print(f"Search error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print("Error response:", e.response.text)
            return {"error": str(e)}

    def infer_with_llama4(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Use Llama 4 for inference with context from search results"""
        headers = {
            "Authorization": f"Bearer {LLAMA_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prepare the context from search results if available
        context_str = ""
        if context and "products" in context:
            context_str = "Based on these search results:\n"
            for product in context["products"]:
                context_str += f"- {product.get('Product Name', 'Unknown')}: {product.get('Price', 'N/A')}\n"
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful shopping assistant. Use the provided context to give detailed, accurate responses."
            }
        ]
        
        if context_str:
            messages.append({
                "role": "system",
                "content": context_str
            })
            
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        body = {
            "model": INFERENCE_MODEL,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.7,
            "top_p": 0.9
        }
        
        try:
            print(f"\nInferring with Llama 4: {prompt[:100]}...")
            response = requests.post(
                LLAMA_URL,
                json=body,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Inference error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print("Error response:", e.response.text)
            return {"error": str(e)}

    def _process_search_results(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Process and format search results"""
        try:
            if "choices" in response:
                content = response["choices"][0]["message"]["content"]
                # Extract product information
                products = []
                current_product = {}
                
                # Split content into lines and process
                lines = content.split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        if current_product:
                            products.append(current_product)
                            current_product = {}
                        continue
                        
                    if line.startswith("- "):
                        line = line[2:]
                        
                    if ":" in line:
                        key, value = line.split(":", 1)
                        current_product[key.strip()] = value.strip()
                    else:
                        if "Product Name" not in current_product:
                            current_product["Product Name"] = line
                
                if current_product:
                    products.append(current_product)
                
                return {
                    "status": "success",
                    "products": products,
                    "raw_content": content
                }
            
            return {"status": "error", "message": "No results found"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_conversation(self, name: str = "Sneaker-Shopping Demo") -> Dict[str, Any]:
        """Create a new Tavus conversation"""
        payload = {
            "persona_id": PERSONA_ID,
            "replica_id": REPLICA_ID,
            "conversation_name": name,
            "conversational_context": (
                "You are a friendly retail assistant who helps customers discover products, answers questions, and assists with secure checkouts. "
                "Ask clarifying questions when needed (e.g., size, color, quantity). "
                "Summarize price and shipping before charging. "
                "Call available tools to fetch product data, generate payment links, and create video confirmations. "
                "If a request is unrelated to shopping or violates policy, politely refuse. "
                "Your goals in every call: "
                "• Understand the shopper's intent (needs, budget, preferred brand, size, color). "
                "• If the shopper asks for information you don't have locally, call the search_product tool to fetch up-to-date results. "
                "• After confirming the exact item, call create_payment_link to generate a secure checkout. "
                "• When the payment link succeeds, call generate_video to record a short confirmation clip that recaps order details and shipping ETA. "
                "• End the call with a polite sign-off and an offer for further help."
            ),
            "properties": {
                "max_call_duration": 900,  # 15 minutes
                "participant_left_timeout": 90,
                "enable_recording": False
            }
        }

        try:
            print("\nCreating conversation with payload:")
            print(json.dumps(payload, indent=2))
            
            response = requests.post(
                TAVUS_CONVERSATION_URL,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"Error response from Tavus API: {response.status_code}")
                print("Response:", response.text)
                return None
                
            data = response.json()
            print("\nResponse from Tavus API:")
            print(json.dumps(data, indent=2))
            
            self.conversation_id = data.get("conversation_id")
            self.conversation_url = data.get("conversation_url")
            
            if not self.conversation_url:
                print("Warning: No conversation URL in response")
                return None
                
            print(f"\n🎥 Conversation created! Join at: {self.conversation_url}")
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"Network error creating conversation: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error creating conversation: {e}")
            return None

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls from the LLM"""
        if tool_name == "search_product":
            results = self.search_product(**arguments)
            # No Llama 4 analysis
            return results
        elif tool_name == "create_payment_link":
            # Implement Stripe integration
            pass
        elif tool_name == "generate_video":
            # Implement Tavus video generation
            pass
        return {"status": "error", "message": f"Unknown tool: {tool_name}"}

def main():
    # Create and test the search agent
    agent = SearchAgent()
    
    # Create a new conversation
    conversation = agent.create_conversation()
    if not conversation:
        print("Failed to create conversation")
        return
    
    # Test product search (no Llama 4 analysis)
    results = agent.search_product("Find Nike Air Force 1 size 10 under $150")
    print("\nSearch Results:")
    print(json.dumps(results, indent=2))
    # No Llama 4 inference

if __name__ == "__main__":
    main() 