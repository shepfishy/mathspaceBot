
# Mathspace Question Solver (i had a little inspiration)

A tool that automatically extracts math questions from Mathspace and uses Google's Gemini AI to provide detailed step-by-step solutions.

## Features

- Automatic login to Mathspace
- Extraction of math questions from too many page elements
- Cleans extracted text to get the actual math problem
- Sending questions to Gemini AI because I don't want to do math

## Prerequisites

- Node.js
- npm
- Google Gemini API key

## Installation

1. Clone the repository
```bash
git clone https://github.com/shepfishy/puppeteer-mathspace.git
cd puppeteer-mathspace
```

2. Install dependencies
```bash
npm install
```

3. Configure your credentials and Gemini API key in `index.js`

## Configuration

Edit the configuration section in `index.js`:

```javascript
const config = {
  credentials: {
    username: 'YOUR_MATHSPACE_USERNAME',
    password: 'YOUR_MATHSPACE_PASSWORD'
  },
  gemini: {
    apiKey: 'YOUR_GEMINI_API_KEY',
    model: 'gemini-2.0-flash',
    promptTemplate: `I need help solving these math problems. Please provide detailed step-by-step solutions. Do not use any text formatting, for instance you can use superscript characters to avoid generating <sup></sup>. Additionally, please answer all questions and subquestions i.e. 1a, and 1b.:

{{QUESTIONS}}

Make sure to show all your work and explain the steps clearly.`
  },
  extractionDelay: 5000 // Wait time after navigation in ms
};
```

## Usage

1. Start the application:
```bash
node index.js
```
or (if you're using npm)
```bash
npm start
```


2. The application will:
   - Launch a browser window
   - Log in to Mathspace with your credentials
   - Wait for you to navigate to a problem page
   - Automatically extract the math question
   - Send them to Gemini AI for solution
   - Display the solutions in the console

3. Navigate to any problem page in Mathspace, and the tool will automatically extract and solve the problems.

## How It Works

1. **Login**: The tool logs into your Mathspace account
2. **Question Extraction**: Extracts potential questions from the page and iframe
3. **API Call**: Sends cleaned questions to Gemini AI
4. **Solutions**: Shows the step by step solution

## Dependencies

- puppeteer: For browser platofrm
- node-fetch: For making API calls to Gemini

## Demonstration

<video src='output.mkv' width=250/>

## License
idfk go away
