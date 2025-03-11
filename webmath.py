from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import os
import requests
import google.generativeai as genai

# Default credentials
DEFAULT_CREDENTIALS = {
    "username": "aruann",
    "password": "6457Backup"
}

# Gemini API Configuration
GEMINI_API_KEY = "AIzaSyA89ILEaCh_4MHRTsnqndrbNy2fXR1suqM"  # Replace with your actual API key
GEMINI_MODEL = "gemini-2.0-flash"  # You can change to other models like 'gemini-1.0-pro' if needed

# Prompt template for math questions
GEMINI_PROMPT_TEMPLATE = """
You are a helpful mathematics assistant.
Please solve the following math problem step by step, showing all your work.
Make sure to explain your reasoning at each step.

PROBLEM:
{question}

Give your solution in a clear, structured format.
"""

# Initialize Gemini API
genai.configure(api_key=GEMINI_API_KEY)

def process_with_gemini(question_text):
    """
    Send the extracted math question to Google Gemini API directly and get a detailed solution
    
    Args:
        question_text (str): The math question to solve
    
    Returns:
        str: The solution provided by Gemini
    """
    print("\nSending question to Gemini AI for analysis...")
    
    try:
        # Format the prompt with the question
        formatted_question = GEMINI_PROMPT_TEMPLATE.format(question=question_text)
        
        # Define the API endpoint with your API key
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        
        # Prepare the request payload
        payload = {
            "contents": [{
                "parts": [{"text": formatted_question}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 8192
            }
        }
        
        # Set headers for the request
        headers = {
            "Content-Type": "application/json"
        }
        
        # Send the POST request to the Gemini API
        response = requests.post(url, json=payload, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            result = response.json()
            
            # Extract the text from the response
            if (result and "candidates" in result and len(result["candidates"]) > 0 and
                "content" in result["candidates"][0] and 
                "parts" in result["candidates"][0]["content"] and
                len(result["candidates"][0]["content"]["parts"]) > 0):
                
                solution_text = result["candidates"][0]["content"]["parts"][0]["text"]
                
                print("\nGEMINI SOLUTION:")
                print("=" * 60)
                print(solution_text)
                print("=" * 60)
                return solution_text
            else:
                print("Error: Unexpected response structure from Gemini API")
                print(f"Response: {result}")
                return "No solution available - API returned unexpected structure"
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return f"Error: API returned status code {response.status_code}"
            
    except Exception as e:
        print(f"Error processing with Gemini: {e}")
        return f"Error: {str(e)}"

def login(driver, credentials=None):
    """
    Logs into Mathspace using the provided credentials
    """
    if not credentials:
        credentials = DEFAULT_CREDENTIALS
        
    print("Logging into Mathspace...")
    
    # Wait for username field and enter username
    username_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#div_id_username input"))
    )
    username_field.send_keys(credentials["username"])
    
    # Click continue button
    continue_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#submit-id-login"))
    )
    continue_btn.click()
    
    # Wait for password field and enter password
    password_field = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "#div_id_password input"))
    )
    password_field.send_keys(credentials["password"])
    
    # Submit login form
    login_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "#submit-id-login"))
    )
    login_btn.click()
    
    # Wait for navigation to complete
    WebDriverWait(driver, 20).until(
        lambda d: "accounts/login" not in d.current_url
    )
    
    print("Login successful")
    return driver

def clean_question_text(text):
    """Clean question text to remove noise and formatting"""
    if not text:
        return ""
    
    # Initial cleaning
    cleaned = text
    
    # Remove promotional text
    cleaned = re.sub(r'Back to School Special:.+?Upgrade', '', cleaned, flags=re.DOTALL)
    
    # Remove section titles with numbering patterns
    cleaned = re.sub(r'\d+\.\d+\s+[A-Za-z]+ in [a-z]+ [a-z]+', '', cleaned)
    
    # Remove excessive numbering while preserving important question numbers
    cleaned = re.sub(r'^\s*\d+\s*\.\s*', '', cleaned)
    
    # Remove dollar signs that might interfere with math expressions
    cleaned = re.sub(r'\$+', '', cleaned)
    
    # Normalize whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove irrelevant UI elements and text
    cleaned = re.sub(r'Help.+', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'Submit.+', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'Toolbox.+?More', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\|\s+', '', cleaned)
    cleaned = re.sub(r'True A False B.+', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'Milo can now speak.*$', '', cleaned, flags=re.MULTILINE)
    
    # Remove buttons and UI text
    cleaned = re.sub(r'Previous Step|Next Step|Show Steps|Hide Steps', '', cleaned)
    
    # Remove timestamps and navigation
    cleaned = re.sub(r'\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(:\d{2})?', '', cleaned)
    
    # Final whitespace cleanup
    cleaned = re.sub(r'\s{2,}', ' ', cleaned).strip()
    
    return cleaned

def detect_problem_id_from_url(url):
    """Extract problem ID from URL"""
    match = re.search(r'/Problem-(\d+)', url)
    if match:
        return match.group(1)
    return None

def extract_questions(driver):
    """
    Extract questions directly from problem header and subproblem divs in Mathspace,
    handling the special case of ordered mathquill-command-id spans
    """
    print("Extracting question text...")
    
    all_question_parts = []
    
    # 1. Find the main problem header
    try:
        problem_header_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'problemHeaderWrapper_')]")
        
        if problem_header_elements:
            main_problem_text = problem_header_elements[0].text.strip()
            if main_problem_text:
                all_question_parts.append(("MAIN PROBLEM", main_problem_text))
                print(f"Found main problem header: {main_problem_text[:50]}...")
                print("\nEXTRACTED MAIN PROBLEM:")
                print("======================")
                print("-" * 60)
                print(main_problem_text)
                print("-" * 60)
    except Exception as e:
        print(f"Error extracting problem header: {e}")
    
    # 2. Find all subproblems with special handling of mathquill spans
    try:
        # Updated to match the correct class name
        subproblem_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'subproblemInstruction_')]")
        
        if subproblem_elements:
            print(f"Found {len(subproblem_elements)} subproblem elements")
            
            for i, subproblem in enumerate(subproblem_elements):
                # CHANGED: Use the fallback text extraction as primary method
                subproblem_text = subproblem.text.strip()
                
                # If the fallback text is good, use it directly
                if subproblem_text and len(subproblem_text) > 5:
                    if not any(input_pattern in subproblem_text.lower() for input_pattern in [
                        "enter your", "type your answer", "insert", "input here"
                    ]):
                        all_question_parts.append((f"SUBPROBLEM {i+1}", subproblem_text))
                        
                        # Display each extracted subquestion
                        print(f"\nEXTRACTED SUBQUESTION {i+1}:")
                        print("=" * 60)
                        print("-" * 60)
                        print(subproblem_text)
                        print("-" * 60)
                        continue  # Go to next subproblem
                
                # Only if fallback didn't work, try the complex extraction with mathquill spans
                # Look for the inner div with class xBQ2HyCNJoo33_Z_K6va if it exists
                inner_divs = subproblem.find_elements(By.CSS_SELECTOR, "div.xBQ2HyCNJoo33_Z_K6va")
                if inner_divs:
                    print(f"Using complex extraction for subproblem {i+1}")
                    
                    for inner_div in inner_divs:
                        # Extract paragraph text if available
                        paragraphs = inner_div.find_elements(By.CSS_SELECTOR, "p")
                        paragraph_texts = [p.text.strip() for p in paragraphs if p.text.strip()]
                        paragraph_content = " ".join(paragraph_texts)
                        
                        # Process math fields
                        math_fields = inner_div.find_elements(By.CSS_SELECTOR, ".mathField_1vyaj94, .mq-math-mode")
                        if math_fields:
                            for math_field in math_fields:
                                # Look for root-block that contains the math content
                                root_blocks = math_field.find_elements(By.CSS_SELECTOR, "span.mq-root-block")
                                if root_blocks:
                                    # Find all spans with mathquill-command-id attributes
                                    command_spans = []
                                    try:
                                        # Use JavaScript to get all spans with the attribute
                                        command_spans = driver.execute_script("""
                                            const span = arguments[0];
                                            return Array.from(span.querySelectorAll('[mathquill-command-id]')).map(el => {
                                                return {
                                                    id: parseInt(el.getAttribute('mathquill-command-id')), 
                                                    text: el.textContent
                                                };
                                            });
                                        """, root_blocks[0])
                                    except Exception as e:
                                        print(f"Error extracting mathquill spans: {e}")
                                    
                                    if command_spans:
                                        # Sort by command ID
                                        command_spans.sort(key=lambda x: x['id'])
                                        
                                        # Extract ordered text
                                        ordered_math_text = ''.join([span['text'] for span in command_spans])
                                        if ordered_math_text:
                                            # Combine paragraph content with math content
                                            combined_content = f"{paragraph_content} {ordered_math_text}".strip()
                                            
                                            if combined_content and not any(input_pattern in combined_content.lower() for input_pattern in [
                                                "enter your", "type your answer", "insert", "input here"
                                            ]):
                                                all_question_parts.append((f"SUBPROBLEM {i+1} (COMPLEX)", combined_content))
                                                
                                                # Display each extracted subquestion
                                                print(f"\nEXTRACTED SUBQUESTION {i+1} (COMPLEX):")
                                                print("=" * 60)
                                                print("-" * 60)
                                                print(combined_content)
                                                print("-" * 60)
                                                
                                                break  # Found a good extraction
    except Exception as e:
        print(f"Error extracting subproblems: {e}")
        import traceback
        traceback.print_exc()
    
    # Check iframes if nothing found in the main document
    if not all_question_parts:
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for i, iframe in enumerate(iframes):
                try:
                    print(f"Checking iframe {i+1}/{len(iframes)}")
                    driver.switch_to.frame(iframe)
                    
                    # Look for problem header in iframe
                    header_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'problemHeaderWrapper_')]")
                    if header_elements:
                        header_text = header_elements[0].text.strip()
                        if header_text:
                            all_question_parts.append(("MAIN PROBLEM (IFRAME)", header_text))
                            print("\nEXTRACTED MAIN PROBLEM (IFRAME):")
                            print("==============================")
                            print("-" * 60)
                            print(header_text)
                            print("-" * 60)
                    
                    # Look for subproblems in iframe with the same special handling
                    sub_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'subproblem_')]")
                    print(f"Found {len(sub_elements)} subproblem elements in iframe")
                    
                    for j, sub in enumerate(sub_elements):
                        # First try text extraction
                        sub_text = sub.text.strip()
                        
                        # Try the special structure
                        prefix_spans = sub.find_elements(By.CSS_SELECTOR, "span.prefix")
                        if prefix_spans:
                            for prefix_span in prefix_spans:
                                root_blocks = prefix_span.find_elements(By.CSS_SELECTOR, "span.mq-root-block")
                                if root_blocks:
                                    command_spans = []
                                    try:
                                        command_spans = driver.execute_script("""
                                            const span = arguments[0];
                                            return Array.from(span.querySelectorAll('span[mathquill-command-id]')).map(el => {
                                                return {
                                                    id: parseInt(el.getAttribute('mathquill-command-id')), 
                                                    text: el.textContent
                                                };
                                            });
                                        """, root_blocks[0])
                                    except:
                                        pass
                                    
                                    if command_spans:
                                        command_spans.sort(key=lambda x: x['id'])
                                        ordered_math_text = ''.join([span['text'] for span in command_spans])
                                        if ordered_math_text:
                                            prefix_text = prefix_span.text.replace(ordered_math_text, '').strip()
                                            math_content = f"{prefix_text} {ordered_math_text}".strip()
                                            
                                            if math_content and not any(input_pattern in math_content.lower() for input_pattern in [
                                                "enter your", "type your answer"
                                            ]):
                                                all_question_parts.append((f"SUBPROBLEM {j+1} (IFRAME)", math_content))
                                                
                                                # Display each extracted subquestion
                                                print(f"\nEXTRACTED SUBQUESTION {j+1} (IFRAME):")
                                                print("=" * 60)
                                                print("-" * 60)
                                                print(math_content)
                                                print("-" * 60)
                                                continue
                        
                        # Use fallback text if needed
                        if sub_text and len(sub_text) > 5 and not any(input_pattern in sub_text.lower() for input_pattern in [
                            "enter your", "type your answer"
                        ]):
                            all_question_parts.append((f"SUBPROBLEM {j+1} (IFRAME)", sub_text))
                            
                            # Display each extracted subquestion
                            print(f"\nEXTRACTED SUBQUESTION {j+1} (IFRAME FALLBACK):")
                            print("=" * 60)
                            print("-" * 60)
                            print(sub_text)
                            print("-" * 60)
                    
                    driver.switch_to.default_content()
                except:
                    driver.switch_to.default_content()
                    continue
        except Exception as e:
            print(f"Error checking iframes: {e}")
            driver.switch_to.default_content()
    
    # Process and clean the extracted text
    if all_question_parts:
        # Format the combined question text
        combined_question = ""
        
        # First add the main problem
        for label, text in all_question_parts:
            if "MAIN PROBLEM" in label:
                cleaned_text = clean_question_text(text)
                if cleaned_text:
                    combined_question += cleaned_text + "\n\n"
                break
        
        # Then add all subproblems
        subproblem_count = 0
        for label, text in all_question_parts:
            if "SUBPROBLEM" in label:
                cleaned_text = clean_question_text(text)
                if cleaned_text:
                    subproblem_count += 1
                    combined_question += f"{subproblem_count}) {cleaned_text}\n\n"
        
        # Remove trailing newlines
        combined_question = combined_question.strip()
        
        if combined_question:
            print("\nFINAL COMBINED QUESTION:")
            print("===================")
            print("-" * 60)
            print(combined_question)
            print("-" * 60)
            return [combined_question]
    
    # Fallback method if the specific classes are not found
    print("Could not find standard problem structure. Trying alternative extraction...")
    
    # Try looking for any math content as a last resort
    try:
        # Look for specific math-related selectors
        math_selectors = [
            ".statement-container", 
            "[data-test='question-text']",
            ".question-text",
            ".problem-text"
        ]
        
        for selector in math_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements and elements[0].text.strip():
                text = elements[0].text.strip()
                cleaned_text = clean_question_text(text)
                if cleaned_text:
                    print("\nFALLBACK EXTRACTION:")
                    print("===================")
                    print("-" * 60)
                    print(cleaned_text)
                    print("-" * 60)
                    return [cleaned_text]
    except Exception as e:
        print(f"Error in fallback extraction: {e}")
    
    print("No valid questions found on page.")
    return []

def monitor_navigation(driver):
    """Monitor page navigation and extract questions when on a problem page"""
    print("Monitoring for problem pages...")
    processed_problems = set()
    last_url = driver.current_url
    
    try:
        while True:
            current_url = driver.current_url
            
            if current_url != last_url:
                print(f"\nDetected navigation to: {current_url}")
                
                # Check if it's a problem page
                problem_id = detect_problem_id_from_url(current_url)
                if problem_id and problem_id not in processed_problems:
                    print(f"Found new problem with ID: {problem_id}")
                    processed_problems.add(problem_id)
                    
                    # Process the current page
                    process_current_page(driver)
                
                last_url = current_url
                
            time.sleep(1)  # Check every second
            
    except KeyboardInterrupt:
        print("Monitoring stopped.")

def process_current_page(driver):
    """
    Process the currently loaded page: extract questions and get a solution from Gemini
    
    Args:
        driver: Selenium webdriver instance with the current problem page loaded
    
    Returns:
        tuple: (question text, solution text, problem_id)
    """
    print("\n" + "="*60)
    print("PROCESSING CURRENT PAGE")
    print("="*60)
    
    current_url = driver.current_url
    problem_id = detect_problem_id_from_url(current_url)
    
    if not problem_id:
        print("No problem ID detected in current URL. Is this a problem page?")
        return None, None, None
    
    print(f"Processing problem with ID: {problem_id}")
    
    # Wait for content to load
    time.sleep(1)
    
    # Extract questions
    questions = extract_questions(driver)
    if not questions or not questions[0]:
        print("No questions could be extracted from this page.")
        return None, None, problem_id
    
    # Process with Gemini
    solution = process_with_gemini(questions[0])
    
    # Save questions and solution to file
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "extracted_questions")
    os.makedirs(save_dir, exist_ok=True)
    
    with open(os.path.join(save_dir, f"problem_{problem_id}.txt"), "w", encoding="utf-8") as f:
        f.write(f"Problem ID: {problem_id}\n")
        f.write(f"URL: {current_url}\n")
        f.write("="*50 + "\n\n")
        f.write("QUESTION:\n")
        f.write(questions[0] + "\n\n")
        f.write("SOLUTION:\n")
        f.write(solution + "\n")
    
    print(f"\nResults saved to {os.path.join(save_dir, f'problem_{problem_id}.txt')}")
    
    return questions[0], solution, problem_id

def open_mathspace(credentials=None):
    """
    Opens mathspace.co using Selenium Chrome webdriver and logs in
    """
    print("Initializing Chrome webdriver...")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # Start with maximized browser
    
    # Initialize the Chrome webdriver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    # Open Mathspace website
    print("Opening mathspace.co...")
    driver.get("https://mathspace.co/accounts/login/")
    
    # Login to Mathspace
    login(driver, credentials)
    
    print("Mathspace.co opened and logged in successfully")
    
    return driver

if __name__ == "__main__":
    driver = None
    try:
        # Import keyboard library for global hotkeys
        import keyboard
        
        # Simply warn about the API key but proceed anyway
        if GEMINI_API_KEY == "AIzaSyA89ILEaCh_4MHRTsnqndrbNy2fXR1suqM":
            print("WARNING: Using default Gemini API key. If it doesn't work, get your own key from: https://aistudio.google.com/apikey")
        
        driver = open_mathspace()
        print("\nBrowser opened and logged in. Navigate to any problem page.")
        print("Questions will be automatically extracted when detected.")
        print("\nKEYBOARD SHORTCUTS:")
        print("  Ctrl+Alt+R: Re-process the current page")
        print("  Ctrl+Alt+Q: Quit the application")
        
        # Start monitoring for problem pages in a separate thread
        import threading
        monitor_thread = threading.Thread(target=monitor_navigation, args=(driver,), daemon=True)
        monitor_thread.start()
        
        # Set up keyboard shortcuts
        def reprocess_page():
            print("\nManually triggered re-processing of current page...")
            process_current_page(driver)
            
        def quit_app():
            print("\nQuitting application...")
            if driver:
                driver.quit()
            import os
            os._exit(0)  # Force exit to terminate all threads
        
        # Register the keyboard shortcuts
        keyboard.add_hotkey('ctrl+alt+r', reprocess_page)
        keyboard.add_hotkey('ctrl+alt+q', quit_app)
        
        # Keep the main thread alive
        print("\nBot is running. Use keyboard shortcuts to control.")
        keyboard.wait('ctrl+alt+q')
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Only clean up if driver exists and is still running
        if driver is not None:
            try:
                print("\nClosing browser...")
                driver.quit()
                print("Browser closed")
            except Exception as e:
                print(f"Error closing browser: {e}")