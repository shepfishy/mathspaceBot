```markdown
# Mathspace Question Solver

A tool that automatically extracts math questions from Mathspace and uses Google's Gemini AI to provide detailed step-by-step solutions.

## Features

- Automatic login to Mathspace
- Detection of problem pages
- Extraction of math questions from various page elements
- Smart cleaning of extracted text to isolate the actual math problems
- Removal of duplicate questions
- Sending questions to Gemini AI for detailed solutions
- Prevention of duplicate API calls for the same problem

## Prerequisites

- Node.js (v14 or higher)
- npm or yarn
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
   - Automatically extract the math questions
   - Send them to Gemini AI for solutions
   - Display the solutions in the console

3. Navigate to any problem page in Mathspace, and the tool will automatically extract and solve the problems.

## How It Works

1. **Login**: The tool logs into your Mathspace account
2. **Navigation Detection**: Listens for navigation to problem pages
3. **Question Extraction**: Extracts potential questions from the page and iframes
4. **Text Cleaning**: Removes promotional content, UI elements, and formatting
5. **Deduplication**: Removes duplicate questions
6. **API Call**: Sends cleaned questions to Gemini AI
7. **Solution Display**: Shows the step-by-step solutions

## Dependencies

- puppeteer: For browser automation
- node-fetch: For making API calls to Gemini

## License
idfk go away
