import asyncio
import os
import re
import time
import json
import requests
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from helpers import log, error, handle_error
import base64
from google import genai
from google.genai import types

# Load environment variables
load_dotenv()

# Configuration - Modify the prompt template
config = {
    "credentials": {
        "username": os.getenv("MATHSPACE_USERNAME"),
        "password": os.getenv("MATHSPACE_PASSWORD")
    },
    "gemini": {
        "apiKey": os.getenv("GEMINI_API_KEY"),
        "model": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        "promptTemplate": """Solve these math problems and provide the answers directly:

{{QUESTIONS}}

Give only the final answers without explanations or steps."""
    },
    "extractionDelay": 5000  # Wait time after navigation in ms
}

# Function to handle login
async def login(page, credentials):
    await page.goto("https://mathspace.co/accounts/login/", timeout=60000)
    await page.wait_for_selector("#div_id_username", state="visible")
    await page.fill("#div_id_username input", credentials["username"])
    
    await page.wait_for_selector("#submit-id-login", state="visible")
    await page.click("#submit-id-login")
    
    await page.wait_for_selector("#div_id_password", state="visible")
    await page.fill("#div_id_password input", credentials["password"])
    
    await page.wait_for_selector("#submit-id-login", state="visible")
    await page.click("#submit-id-login")
    
    await page.wait_for_load_state("networkidle")
    log("Login successful")

# Function to extract multiple question candidates from page and frames
async def extract_question_candidates(page):
    candidates = []
    
    # Try to extract from main page first
    main_page_candidates = await page.evaluate("""() => {
        const allCandidates = [];
        
        // METHOD 1: Check specific containers
        const containerSelectors = [
            '.question-text',
            '.statement-container',
            '.problem-text',
            '.rendered-content',
            '.jsx-content',
            '[data-test="question-text"]',
            '.adapted-step-statement',
            '.lesson-content'
        ];
        
        for (const selector of containerSelectors) {
            const containers = document.querySelectorAll(selector);
            for (const container of containers) {
                const text = container.innerText.trim();
                if (text && text.length > 15) {
                    allCandidates.push(text);
                }
            }
        }
        
        // METHOD 2: Find paragraphs with mathematical content
        const mathTerms = ['simplify', 'solve', 'calculate', 'find', 'evaluate', 'determine', 'prove', 'factor', 'expand'];
        const mathSymbols = ['=', '+', '-', '×', '÷', '<', '>', '≤', '≥', '∫', '∑', '√', '∞', 'π', '∆', '∇', '∂', '∈', '∉', '∴', '∵', '≠', '≈'];
        
        const paragraphs = Array.from(document.querySelectorAll('p, div'))
            .filter(el => {
                const text = el.innerText.trim();
                if (text.length < 15 || text.length > 500) return false;
                
                // Check for math terminology
                for (const term of mathTerms) {
                    if (text.toLowerCase().includes(term)) return true;
                }
                
                // Check for math symbols
                for (const symbol of mathSymbols) {
                    if (text.includes(symbol)) return true;
                }
                
                // Check for algebraic expressions (variables with exponents)
                if (/[a-z]\\^?\\d+/.test(text)) return true;
                
                // Check for coordinates, equations
                if (text.includes('(') && text.includes(')')) return true;
                
                return false;
            })
            .map(el => el.innerText.trim());
        
        return [...allCandidates, ...paragraphs];
    }""")
    
    candidates.extend(main_page_candidates)
    
    # Check frames for content
    frames = page.frames
    
    for i, frame in enumerate(frames):
        try:
            log(f"Checking frame {i+1}/{len(frames)}")
            
            frame_candidates = await frame.evaluate("""() => {
                const allCandidates = [];
                
                // Same methods as above
                const containerSelectors = [
                    '.question-text',
                    '.statement-container', 
                    '.problem-text',
                    '.rendered-content',
                    '.jsx-content'
                ];
                
                for (const selector of containerSelectors) {
                    const containers = document.querySelectorAll(selector);
                    for (const container of containers) {
                        const text = container.innerText.trim();
                        if (text && text.length > 15) {
                            allCandidates.push(text);
                        }
                    }
                }
                
                // METHOD 2: Mathematical paragraphs using the same criteria
                const mathTerms = ['simplify', 'solve', 'calculate', 'find', 'evaluate', 'determine', 'prove', 'factor', 'expand'];
                const mathSymbols = ['=', '+', '-', '×', '÷', '<', '>', '≤', '≥', '∫', '∑', '√', '∞', 'π', '∆', '∇', '∂', '∈', '∉', '∴', '∵', '≠', '≈'];
                
                const paragraphs = Array.from(document.querySelectorAll('p, div'))
                    .filter(el => {
                        const text = el.innerText.trim();
                        if (text.length < 15 || text.length > 500) return false;
                        
                        for (const term of mathTerms) {
                            if (text.toLowerCase().includes(term)) return true;
                        }
                        
                        for (const symbol of mathSymbols) {
                            if (text.includes(symbol)) return true;
                        }
                        
                        if (/[a-z]\\^?\\d+/.test(text)) return true;
                        
                        if (text.includes('(') && text.includes(')')) return true;
                        
                        return false;
                    })
                    .map(el => el.innerText.trim());
                
                return [...allCandidates, ...paragraphs];
            }""")
            
            candidates.extend(frame_candidates)
        except Exception as e:
            log(f"Error accessing frame {i+1}: {str(e)}")
    
    log(f"Found {len(candidates)} question candidates")
    
    # Display all candidate questions
    print('\nALL QUESTION CANDIDATES:')
    print('=======================')
    for i, candidate in enumerate(candidates):
        print(f"\nCANDIDATE #{i + 1}:")
        print('--------------')
        print(candidate)
        print('--------------')
    
    return candidates

# Clean and score question text
def clean_question_text(text):
    if not text:
        return ''
    
    # Initial cleaning to standardize the text
    cleaned = text
    cleaned = re.sub(r'Back to School Special:.+?Upgrade', '', cleaned)  # Remove promotional text
    cleaned = re.sub(r'\d+\.\d+\s+[A-Za-z]+ in [a-z]+ [a-z]+', '', cleaned)  # Remove section titles
    cleaned = re.sub(r'\s*\d+\s*\.\s*', '', cleaned)  # Remove numbering
    cleaned = re.sub(r'\$+', '', cleaned)  # Remove dollar signs
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
    cleaned = re.sub(r'Help.+', '', cleaned, flags=re.DOTALL)  # Remove everything after Help
    cleaned = re.sub(r'Submit.+', '', cleaned, flags=re.DOTALL)  # Remove everything after Submit
    cleaned = re.sub(r'Toolbox.+?More', '', cleaned, flags=re.DOTALL)  # Remove toolbox text
    cleaned = re.sub(r'\|\s+', '', cleaned)  # Remove separator characters
    cleaned = re.sub(r'True A False B.+', '', cleaned, flags=re.DOTALL)  # Remove answer options
    cleaned = re.sub(r'Milo can now speak.*$', '', cleaned, flags=re.MULTILINE)  # Remove Milo notifications
    cleaned = cleaned.strip()
    
    return cleaned

# Function to prepare all questions for sending to Gemini
def prepare_all_questions(candidates):
    if not candidates or len(candidates) == 0:
        return None
    
    # Clean all candidates and filter out invalid ones
    cleaned_questions = [clean_question_text(question) for question in candidates]
    cleaned_questions = [q for q in cleaned_questions if len(q) >= 15]
    
    # Remove duplicates
    unique_questions = list(set(cleaned_questions))
    
    if not unique_questions:
        return None
    
    # Join questions with line breaks
    formatted_questions = '\n\n'.join(unique_questions)
    
    # Use the template from config, replacing the placeholder with the actual questions
    final_prompt = config['gemini']['promptTemplate'].replace('{{QUESTIONS}}', formatted_questions)
    
    # Still show question numbers in console for clarity
    print('\nCLEANED QUESTIONS:')
    print('=================')
    for idx, q in enumerate(unique_questions):
        print(f"\nQuestion {idx+1}:")
        print('--------------')
        print(q)
        print('--------------')
    
    print('\nFINAL PROMPT FOR GEMINI:')
    print('=======================')
    print(final_prompt)
    print('=======================\n')
    
    return final_prompt

# Function to validate question text
def is_valid_question(text):
    return text and text != 'Could not find question text' and len(text) >= 15

# Function to send question to Gemini API with structured output
def send_to_gemini(prompt, gemini_config):
    try:
        print('\nSENDING ALL QUESTIONS TO GEMINI:')
        print('==============================')
        print('Sending all extracted questions to Gemini in one call...')
        
        # Initialize the client with API key
        client = genai.Client(api_key=gemini_config['apiKey'])
        
        model = gemini_config['model']
        
        # Configure the generation parameters with updated instructions
        generate_content_config = types.GenerateContentConfig(
            temperature=1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="application/json",
            response_schema=genai.types.Schema(
                type=genai.types.Type.OBJECT,
                required=["answer", "confidenceOutOf10"],
                properties={
                    "answer": genai.types.Schema(
                        type=genai.types.Type.STRING,
                        description="The final answer without explanations or steps"
                    ),
                    "confidenceOutOf10": genai.types.Schema(
                        type=genai.types.Type.NUMBER,
                    ),
                },
            ),
            system_instruction=[
                types.Part.from_text(text="""You are a math problem solver. Provide ONLY the final answers to math problems without any explanations, steps, or workings. Return your response in a structured JSON format with 'answer' and 'confidenceOutOf10' fields."""),
            ],
        )
        
        # Rest of the function remains the same
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            )
        ]

        print('\nGEMINI RESPONSE:')
        print('================')
        
        # Collect the full response
        full_response = ""
        
        # Generate the content with streaming
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=generate_content_config,
        ):
            if chunk.text:
                print(chunk.text, end="")
                full_response += chunk.text
        
        print('\n================\n')
        
        # Try to parse the JSON response for further processing if needed
        try:
            import json
            response_json = json.loads(full_response)
            return response_json
        except json.JSONDecodeError:
            print("Warning: Couldn't parse response as JSON")
            return {"answer": full_response, "confidenceOutOf10": 0}
            
    except Exception as e:
        error(f'Error calling Gemini API: {str(e)}')
        return None

# Add this function to handle filling in answers and submitting
async def fill_and_submit_answer(page, answer):
    try:
        print(f"\nAttempting to fill in answer: {answer}")
        
        # Wait for the math field to be available
        await page.wait_for_selector(".mathField_tck2f6-o_O-primaryLatexInput_1hzh0y1", timeout=5000)
        
        # Click on the math field to ensure it's active
        await page.click(".mathField_tck2f6-o_O-primaryLatexInput_1hzh0y1")
        
        # Clear any existing content first (by pressing Ctrl+A and then Delete)
        await page.keyboard.press("Control+a")
        await page.keyboard.press("Delete")
        
        # Type the answer
        await page.keyboard.type(answer.strip())
        
        print("Answer typed into field")
        
        # Wait a moment for the field to update
        await page.wait_for_timeout(1000)
        
        # Check if submit button is enabled
        submit_button = await page.query_selector("button[aria-label='Submit step']")
        is_disabled = await submit_button.get_attribute("aria-disabled") == "true"
        
        if not is_disabled:
            print("Clicking submit button...")
            await submit_button.click()
            print("Answer submitted!")
        else:
            print("Submit button is disabled. Please check if the answer format is correct.")
        
    except Exception as e:
        print(f"Error filling in answer: {str(e)}")

# Update the process_problem function to use the fill_and_submit_answer function
async def process_problem(problem_id):
    global processing_in_progress
    processing_in_progress = True
    
    try:
        print(f"\nDetected problem page with ID: {problem_id}")
        print(f"URL: {page.url}")
        print(f"Waiting {config['extractionDelay']/1000} seconds for content to load...")
        
        await page.wait_for_timeout(config['extractionDelay'])
        
        # Extract question candidates
        question_candidates = await extract_question_candidates(page)
        
        # Clean all questions and prepare final prompt
        final_prompt = prepare_all_questions(question_candidates)
        
        # Send to Gemini API
        if final_prompt:
            response = send_to_gemini(final_prompt, config['gemini'])
            
            if response and 'answer' in response:
                # Extract the answer from response
                answer = response['answer']
                
                # Fill in and submit the answer
                await fill_and_submit_answer(page, answer)
            else:
                print('No valid answer found in Gemini response.')
        else:
            print('No valid questions found. Skipping Gemini API call.')
    except Exception as e:
        handle_error(e)
    finally:
        processing_in_progress = False

# Main function
async def main():
    # Define processing_in_progress at global scope first
    global processing_in_progress
    processing_in_progress = False
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        
        try:
            context = await browser.new_context(viewport=None)
            page = await context.new_page()
            
            # Track processed problem IDs to prevent duplicate API calls
            processed_problem_ids = set()
            last_url = ""
            
            # Login to Mathspace
            log('Logging into Mathspace...')
            await login(page, config['credentials'])
            
            print('\nPlease navigate to any problem page.')
            # Function to process the problem page
            async def process_problem(problem_id):
                global processing_in_progress
                processing_in_progress = True
                processing_in_progress = True
                
                try:
                    print(f"\nDetected problem page with ID: {problem_id}")
                    print(f"URL: {page.url}")
                    print(f"Waiting {config['extractionDelay']/1000} seconds for content to load...")
                    
                    await page.wait_for_timeout(config['extractionDelay'])
                    
                    # Extract question candidates
                    question_candidates = await extract_question_candidates(page)
                    
                    # Clean all questions and prepare final prompt
                    final_prompt = prepare_all_questions(question_candidates)
                    
                    # Send to Gemini API
                    if final_prompt:
                        send_to_gemini(final_prompt, config['gemini'])
                    else:
                        print('No valid questions found. Skipping Gemini API call.')
                except Exception as e:
                    handle_error(e)
                finally:
                    processing_in_progress = False
            
            # Set up a periodic check for URL changes
            while True:
                await asyncio.sleep(1)  # Check every second
                current_url = page.url
                
                if current_url != last_url and not processing_in_progress:
                    last_url = current_url
                    
                    # Debug: Print URL change detection
                    print(f"URL changed to: {current_url}")
                    
                    # Check for problem ID in URL
                    problem_id_match = re.search(r'/Problem-(\d+)', current_url)
                    
                    if problem_id_match and problem_id_match.group(1):
                        problem_id = problem_id_match.group(1)
                        
                        # MODIFIED: Only check for problem ID if on a mathspace.co domain
                        if "mathspace.co" in current_url:
                            # Process every problem we navigate to, regardless of history
                            print(f"\nProcessing problem ID: {problem_id}")
                            await process_problem(problem_id)
            
        except Exception as e:
            error(f'An error occurred: {str(e)}')
        finally:
            # This line is commented out to keep the browser open
            # await browser.close()
            # Instead, wait for user to manually close
            try:
                # Keep the script running until user interrupts
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                await browser.close()
                print("Browser closed by user")

# Run the main function
if __name__ == "__main__":
    asyncio.run(main())