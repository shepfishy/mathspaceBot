const puppeteer = require('puppeteer');
const fetch = require('node-fetch');

// Configuration
const config = {
  credentials: {
    username: 'aruann',
    password: '6457Backup'
  },
  gemini: {
    apiKey: 'AIzaSyA89ILEaCh_4MHRTsnqndrbNy2fXR1suqM', // Replace with your actual API key
    model: 'gemini-2.0-flash',
    promptTemplate: `I need help solving these math problems. Please provide detailed step-by-step solutions. Do not use any text formatting, for instance you can use superscript characters to avoid generating <sup></sup>. Additionally, please answer all questions and subquestions i.e. 1a, and 1b.:

{{QUESTIONS}}

Make sure to show all your work and explain the steps clearly.`
  },
  extractionDelay: 5000 // Wait time after navigation
};

// Main function with improved navigation handling
(async () => {
  // Initialize browser
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    args: ['--start-maximized', '--no-sandbox', '--disable-setuid-sandbox']
  });

  try {
    const page = await browser.newPage();
    
    // Track processed problem IDs to prevent duplicate API calls
    const processedProblemIds = new Set();
    let processingInProgress = false;
    let debounceTimer = null;
    
    // ===============================
    // STEP 1: LOGIN TO MATHSPACE
    // ===============================
    console.log('Logging into Mathspace...');
    await login(page, config.credentials);
    console.log('Login successful');
    
    // ===============================
    // STEP 2: NAVIGATION HANDLER
    // ===============================
    console.log('\nPlease navigate to any problem page.');
    
    // Set up navigation detector with debouncing
    page.on('framenavigated', async frame => {
      if (frame === page.mainFrame() && !processingInProgress) {
        const url = frame.url();
        
        // Extract problem ID using regex to ensure we don't process the same problem multiple times
        const problemIdMatch = url.match(/\/Problem-(\d+)/);
        
        if (problemIdMatch && problemIdMatch[1]) {
          const problemId = problemIdMatch[1];
          
          // Clear any existing debounce timer
          if (debounceTimer) {
            clearTimeout(debounceTimer);
          }
          
          // Set a new debounce timer
          debounceTimer = setTimeout(async () => {
            // Check if we've already processed this problem ID
            if (!processedProblemIds.has(problemId)) {
              processedProblemIds.add(problemId); // Mark problem ID as processed
              processingInProgress = true;
              
              try {
                console.log(`\nDetected problem page with ID: ${problemId}`);
                console.log(`URL: ${url}`);
                console.log(`Waiting ${config.extractionDelay/1000} seconds for content to load...`);
                await page.waitForTimeout(config.extractionDelay);
                
                // ===============================
                // STEP 3: EXTRACT QUESTION CANDIDATES
                // ===============================
                const questionCandidates = await extractQuestionCandidates(page);
                
                // ===============================
                // STEP 4: CLEAN ALL QUESTIONS
                // ===============================
                const finalPrompt = prepareAllQuestions(questionCandidates);
                
                // ===============================
                // STEP 5: SEND ALL TO GEMINI API
                // ===============================
                if (finalPrompt) {
                  await sendToGemini(finalPrompt, config.gemini);
                } else {
                  console.log('No valid questions found. Skipping Gemini API call.');
                }
              } catch (error) {
                console.error('Error processing problem:', error);
              } finally {
                processingInProgress = false;
              }
            } else {
              console.log(`\nSkipping already processed problem ID: ${problemId}`);
            }
          }, 1000); // 1-second debounce
        }
      }
    });
    
    // Keep browser open
    // await browser.close();
  } catch (error) {
    console.error('An error occurred:', error);
    await browser.close();
  }
})();

// Function to handle login
async function login(page, credentials) {
  await page.goto('https://mathspace.co/accounts/login/', { 
    waitUntil: 'networkidle2', 
    timeout: 60000 
  });
  
  // Enter username
  await page.waitForSelector('#div_id_username', { visible: true });
  await page.type('#div_id_username input', credentials.username);
  
  // Click continue button
  await page.waitForSelector('#submit-id-login', { visible: true });
  await page.click('#submit-id-login');
  
  // Enter password
  await page.waitForSelector('#div_id_password', { visible: true });
  await page.type('#div_id_password input', credentials.password);
  
  // Submit login form
  await page.waitForSelector('#submit-id-login', { visible: true });
  await page.click('#submit-id-login');
  
  // Wait for navigation to complete
  return page.waitForNavigation({ waitUntil: 'networkidle2' });
}

// Function to extract multiple question candidates from page and frames
async function extractQuestionCandidates(page) {
  const candidates = [];
  
  // Try to extract from main page first
  const mainPageCandidates = await page.evaluate(() => {
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
        if (/[a-z]\^?\d+/.test(text)) return true;
        
        // Check for coordinates, equations
        if (text.includes('(') && text.includes(')')) return true;
        
        return false;
      })
      .map(el => el.innerText.trim());
    
    return [...allCandidates, ...paragraphs];
  });
  
  candidates.push(...mainPageCandidates);
  
  // Check frames for content
  const frames = page.frames();
  
  for (let i = 0; i < frames.length; i++) {
    try {
      console.log(`Checking frame ${i+1}/${frames.length}`);
      
      const frameCandidates = await frames[i].evaluate(() => {
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
            
            if (/[a-z]\^?\d+/.test(text)) return true;
            
            if (text.includes('(') && text.includes(')')) return true;
            
            return false;
          })
          .map(el => el.innerText.trim());
        
        return [...allCandidates, ...paragraphs];
      });
      
      candidates.push(...frameCandidates);
    } catch (e) {
      console.log(`Error accessing frame ${i+1}: ${e.message}`);
    }
  }
  
  console.log(`Found ${candidates.length} question candidates`);
  
  // Display all candidate questions
  console.log('\nALL QUESTION CANDIDATES:');
  console.log('=======================');
  candidates.forEach((candidate, index) => {
    console.log(`\nCANDIDATE #${index + 1}:`);
    console.log('--------------');
    console.log(candidate);
    console.log('--------------');
  });
  
  return candidates;
}

// Clean and score question text
function cleanQuestionText(text) {
  if (!text) return '';
  
  // Initial cleaning to standardize the text
  let cleaned = text
    .replace(/Back to School Special:.+?Upgrade/g, '') // Remove promotional text
    .replace(/\d+\.\d+\s+[A-Za-z]+ in [a-z]+ [a-z]+/g, '') // Remove section titles
    .replace(/\s*\d+\s*\.\s*/, '') // Remove numbering
    .replace(/\$+/g, '') // Remove dollar signs
    .replace(/\s+/g, ' ') // Normalize whitespace
    .replace(/Help.+/s, '') // Remove everything after Help
    .replace(/Submit.+/s, '') // Remove everything after Submit
    .replace(/Toolbox.+?More/s, '') // Remove toolbox text
    .replace(/\|\s+/g, '') // Remove separator characters
    .replace(/True A False B.+/s, '') // Remove answer options
    .replace(/Milo can now speak.*$/m, '') // Remove Milo notifications
    .trim();
  
  return cleaned;
}

// Function to prepare all questions for sending to Gemini
function prepareAllQuestions(candidates) {
  if (!candidates || candidates.length === 0) {
    return null;
  }
  
  // Clean all candidates and filter out invalid ones
  const cleanedQuestions = candidates
    .map(question => cleanQuestionText(question))
    .filter(question => question.length >= 15);
  
  // Remove duplicates
  const uniqueQuestions = [...new Set(cleanedQuestions)];
  
  if (uniqueQuestions.length === 0) {
    return null;
  }
  
  // Join questions with line breaks
  const formattedQuestions = uniqueQuestions.join('\n\n');
  
  // Use the template from config, replacing the placeholder with the actual questions
  const finalPrompt = config.gemini.promptTemplate.replace('{{QUESTIONS}}', formattedQuestions);
  
  // Still show question numbers in console for clarity
  console.log('\nCLEANED QUESTIONS:');
  console.log('=================');
  uniqueQuestions.forEach((q, idx) => {
    console.log(`\nQuestion ${idx+1}:`);
    console.log('--------------');
    console.log(q);
    console.log('--------------');
  });
  
  console.log('\nFINAL PROMPT FOR GEMINI:');
  console.log('=======================');
  console.log(finalPrompt);
  console.log('=======================\n');
  
  return finalPrompt;
}

// Function to validate question text
function isValidQuestion(text) {
  return text && 
         text !== 'Could not find question text' && 
         text.length >= 15;
}

// Function to send question to Gemini API
async function sendToGemini(prompt, geminiConfig) {
  try {
    console.log('\nSENDING ALL QUESTIONS TO GEMINI:');
    console.log('==============================');
    console.log('Sending all extracted questions to Gemini in one call...');
    
    const response = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/${geminiConfig.model}:generateContent?key=${geminiConfig.apiKey}`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: prompt
            }]
          }]
        })
      }
    );
    
    const data = await response.json();
    
    console.log('\nGEMINI RESPONSE:');
    console.log('================');
    
    if (data.candidates && data.candidates[0] && data.candidates[0].content) {
      const responseText = data.candidates[0].content.parts[0].text;
      console.log(responseText);
    } else if (data.error) {
      console.log('Error:', data.error.message);
    } else {
      console.log('Unexpected API response format:', JSON.stringify(data, null, 2));
    }
    
    console.log('================\n');
  } catch (error) {
    console.error('Error calling Gemini API:', error);
  }
}