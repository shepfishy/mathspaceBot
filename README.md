
# Mathspace Question Solver (i had a little inspiration)

A tool that automatically extracts math questions from Mathspace and uses Google's Gemini AI to provide detailed step-by-step solutions.

## Features

- Automatic login to Mathspace
- Extraction of math questions from too many page elements
- Cleans extracted text to get the actual math problem
- Sending questions to Gemini AI because I don't want to do math

## Prerequisites

- Python 3.11 or 3.12 and Pip
- Google Gemini API key

## Installation

1. Clone the repository
```bash
git clone https://github.com/shepfishy/puppeteer-mathspace.git
cd puppeteer-mathspace
```

2. Install dependencies
```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 -m playwright install
```

3. Create a .env file using the .env.example file and set your credentials and API Key

## Usage

1. Start the application:
```bash
py -3.12 main.py
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

## Demonstration
``` output.mkv ```
<video src='output.mkv' width=250/>

## License
idfk go away
