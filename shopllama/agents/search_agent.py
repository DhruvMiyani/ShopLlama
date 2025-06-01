import os
import requests
import json
import webbrowser
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Load environment variables
load_dotenv()

# API Keys
TAVUS_API_KEY = "ff5322363aed4974bfa4b5feb2891c3f"
PPLX_API_KEY = "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"

# Model Configuration
SEARCH_MODEL = "sonar"  # For product search via Perplexity

# Tavus Configuration
PERSONA_ID = "p9a95912"  # Demo Persona ID
REPLICA_ID = "r79e1c033f"  # Demo Persona's replica ID

# API Endpoints
TAVUS_API_BASE = "https://tavusapi.com/v2"
TAVUS_CONVERSATION_URL = f"{TAVUS_API_BASE}/conversations"
TAVUS_PERSONA_URL = f"{TAVUS_API_BASE}/personas"
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

class CheckoutAgent:
    def __init__(self):
        self.driver = None
        self.current_product = None
        
    def start_browser(self):
        """Initialize the browser"""
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        self.driver = webdriver.Chrome(options=options)
        
    def close_browser(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            
    def add_to_cart(self, product_url: str, size: str = None) -> bool:
        """Add product to cart"""
        try:
            if not self.driver:
                self.start_browser()
                
            # Navigate to product page
            self.driver.get(product_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Handle size selection if provided
            if size:
                try:
                    # Try different size selector patterns
                    size_selectors = [
                        f"//button[contains(text(), '{size}')]",
                        f"//div[contains(@class, 'size')]//button[contains(text(), '{size}')]",
                        f"//select[contains(@class, 'size')]//option[contains(text(), '{size}')]"
                    ]
                    
                    for selector in size_selectors:
                        try:
                            size_element = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                            size_element.click()
                            break
                        except:
                            continue
                            
                except TimeoutException:
                    print(f"Size {size} not found, proceeding without size selection")
            
            # Find and click add to cart button with multiple patterns
            add_to_cart_selectors = [
                "//button[contains(text(), 'Add to Cart')]",
                "//button[contains(text(), 'Add to Bag')]",
                "//button[contains(@class, 'add-to-cart')]",
                "//button[contains(@class, 'add-to-bag')]",
                "//div[contains(@class, 'add-to-cart')]//button",
                "//div[contains(@class, 'add-to-bag')]//button"
            ]
            
            for selector in add_to_cart_selectors:
                try:
                    add_to_cart_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    add_to_cart_button.click()
                    break
                except:
                    continue
            
            # Wait for confirmation
            confirmation_selectors = [
                "//*[contains(text(), 'Added to Cart')]",
                "//*[contains(text(), 'Added to Bag')]",
                "//*[contains(@class, 'success-message')]"
            ]
            
            for selector in confirmation_selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    return True
                except:
                    continue
            
            return True  # Return True if we clicked the button, even if confirmation isn't found
            
        except Exception as e:
            print(f"Error adding to cart: {e}")
            return False
            
    def proceed_to_checkout(self) -> bool:
        """Proceed to checkout page"""
        try:
            # Find and click checkout button with multiple patterns
            checkout_selectors = [
                "//button[contains(text(), 'Checkout')]",
                "//button[contains(text(), 'Proceed to Checkout')]",
                "//a[contains(text(), 'Checkout')]",
                "//a[contains(text(), 'Proceed to Checkout')]",
                "//div[contains(@class, 'checkout')]//button",
                "//div[contains(@class, 'checkout')]//a"
            ]
            
            for selector in checkout_selectors:
                try:
                    checkout_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    checkout_button.click()
                    break
                except:
                    continue
            
            # Wait for checkout page to load
            checkout_page_selectors = [
                "//*[contains(text(), 'Checkout')]",
                "//*[contains(text(), 'Shipping')]",
                "//*[contains(text(), 'Payment')]",
                "//*[contains(@class, 'checkout')]"
            ]
            
            for selector in checkout_page_selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    return True
                except:
                    continue
            
            return True  # Return True if we clicked the button, even if confirmation isn't found
            
        except Exception as e:
            print(f"Error proceeding to checkout: {e}")
            return False

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
        self.checkout_agent = CheckoutAgent()
        self.selected_product = None
        self.last_search_results = None
        
        # Validate API keys on initialization
        self._validate_api_keys()
        
        # Create or get persona
        self.persona_id = self._setup_persona()

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

    def _setup_persona(self) -> str:
        """Create or get the shopping assistant persona"""
        persona_data = {
            "system_prompt": (
                "You are a friendly retail assistant who helps customers discover products, "
                "answers questions, and assists with secure checkouts. "
                "Use the search results provided to give accurate product information."
            ),
            "conversational_context": (
                "You are a friendly retail assistant who helps customers discover products, "
                "answers questions, and assists with secure checkouts. "
                "Ask clarifying questions when needed (e.g., size, color, quantity). "
                "Summarize price and shipping before charging. "
                "If a request is unrelated to shopping or violates policy, politely refuse."
            ),
            "layers": {
                "llm": {
                    "model": "tavus-llama",
                    "speculative_inference": True
                },
                "perception": {
                    "model": "default"
                },
                "stt": {
                    "engine": "whisper",
                    "language": "en"
                },
                "tts": {
                    "engine": "elevenlabs",
                    "voice_id": "default"
                }
            }
        }
        
        try:
            # Try to create new persona
            response = requests.post(
                TAVUS_PERSONA_URL,
                headers=self.headers,
                json=persona_data
            )
            if response.status_code == 200:
                return response.json()["id"]
            elif response.status_code == 409:  # Persona already exists
                # Get existing persona
                response = requests.get(
                    f"{TAVUS_PERSONA_URL}/{PERSONA_ID}",
                    headers=self.headers
                )
                if response.status_code == 200:
                    return PERSONA_ID
            raise Exception(f"Failed to setup persona: {response.text}")
        except Exception as e:
            print(f"Error setting up persona: {e}")
            return PERSONA_ID  # Fallback to default persona

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
        """Create a new Tavus conversation with STT/TTS enabled"""
        payload = {
            "persona_id": self.persona_id,
            "replica_id": REPLICA_ID,
            "conversation_name": name,
            "properties": {
                "max_call_duration": 900,
                "participant_left_timeout": 90,
                "enable_recording": True
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

    def handle_user_input(self, user_input: str) -> Dict[str, Any]:
        """Handle user input, perform search, and prepare response"""
        # Check if user wants to checkout
        if "checkout" in user_input.lower() or "buy" in user_input.lower():
            if self.last_search_results:
                # Extract product number if specified
                import re
                product_num = re.search(r'checkout\s+(\d+)', user_input.lower())
                if product_num:
                    try:
                        idx = int(product_num.group(1)) - 1
                        if 0 <= idx < len(self.last_search_results.get("products", [])):
                            self.selected_product = self.last_search_results["products"][idx]
                            return self._handle_checkout()
                    except:
                        pass
                
                # If no specific product number, use the first product
                if not self.selected_product and self.last_search_results.get("products"):
                    self.selected_product = self.last_search_results["products"][0]
                    return self._handle_checkout()
            
            return {
                "status": "error",
                "message": "Please search for a product first, then say 'checkout' or 'checkout [number]' to select a specific product."
            }
        
        # First, search for products
        search_results = self.search_product(user_input)
        self.last_search_results = search_results
        
        if search_results.get("status") == "success":
            # Format search results for the persona
            products_text = "Here are the products I found:\n"
            for idx, product in enumerate(search_results["products"]):
                if not product.get("Product Name") or product["Product Name"].strip() == "---":
                    continue
                products_text += f"\n{idx + 1}. {product.get('Product Name')}\n"
                for k, v in product.items():
                    if k != "Product Name":
                        products_text += f"   {k}: {v}\n"
            
            # Add checkout instructions
            products_text += "\nTo checkout a product, say 'checkout' or 'checkout [number]' to select a specific product."
            
            # Send to Tavus for response
            response = requests.post(
                f"{TAVUS_API_BASE}/conversations/{self.conversation_id}/messages",
                headers=self.headers,
                json={
                    "content": products_text,
                    "role": "assistant"
                }
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "search_results": search_results,
                    "persona_response": response.json()
                }
        
        return {
            "status": "error",
            "message": "Failed to process user input"
        }

    def _handle_checkout(self) -> Dict[str, Any]:
        """Handle the checkout process for selected product"""
        try:
            if not self.selected_product:
                return {
                    "status": "error",
                    "message": "No product selected for checkout"
                }
            
            # Extract product URL from search results
            product_url = None
            if "Where to buy" in self.selected_product:
                if "nike.com" in self.selected_product["Where to buy"].lower():
                    product_url = "https://www.nike.com"
                elif "footlocker" in self.selected_product["Where to buy"].lower():
                    product_url = "https://www.footlocker.com"
                elif "amazon.com" in self.selected_product["Where to buy"].lower():
                    product_url = "https://www.amazon.com"
            
            if not product_url:
                return {
                    "status": "error",
                    "message": "Could not determine product URL"
                }
            
            # Add to cart
            if self.checkout_agent.add_to_cart(product_url):
                # Proceed to checkout
                if self.checkout_agent.proceed_to_checkout():
                    return {
                        "status": "success",
                        "message": "Successfully added to cart and proceeded to checkout! The browser window is now open for you to complete the purchase."
                    }
            
            return {
                "status": "error",
                "message": "Failed to complete checkout process"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error during checkout: {str(e)}"
            }

def main():
    # Create and test the search agent
    agent = SearchAgent()
    
    # Create a new conversation
    conversation = agent.create_conversation()
    if not conversation:
        print("Failed to create conversation")
        return
    
    print("\n🎥 Join the conversation at:", agent.conversation_url)
    print("Type 'exit' to end the conversation")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            agent.checkout_agent.close_browser()
            break
            
        response = agent.handle_user_input(user_input)
        if response["status"] == "success":
            print("\nAssistant:", response["persona_response"].get("content", "No response"))
        else:
            print("\nError:", response.get("message", "Unknown error"))

if __name__ == "__main__":
    main() 