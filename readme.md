# Mathspace Bot

A Python automation tool that extracts math problems from Mathspace and solves them using Google's Gemini AI.

## Features

- **Automatic Problem Detection**: Monitors Mathspace navigation and detects when you visit a problem page
- **Smart Extraction**: Extracts both problem headers and subproblems from various Mathspace page structures
- **AI-Powered Solutions**: Uses Google's Gemini AI to generate step-by-step solutions
- **Problem Saving**: Automatically saves questions and solutions to text files for later review
- **Keyboard Shortcuts**: Control the bot using convenient keyboard combinations

## Prerequisites

- Python 3.12.2
- Google Chrome browser
- A Gemini API key (get one from [Google AI Studio](https://aistudio.google.com/apikey))
- Administrator privileges (required for keyboard shortcuts)

## Installation

1. Clone this repository or download the code:

   ```
   git clone https://github.com/shepfishy/puppeteer-mathspace.git
   cd puppeteer-mathspace
   ```

2. Install the required Python packages:

   ```
   pip install -r requirements.txt
   ```

3. Run the bot:

    Linux:
   ```
   python webmath.py
   ```

    Windows:
   ```
   py webmath.py
   ```

4. The bot will open Chrome, log into Mathspace, and start monitoring for problem pages.

## Usage

1. Navigate to any math problem on Mathspace. The bot will automatically:
   - Extract the question text
   - Send it to Gemini AI for solving
   - Save the question and solution to a file in the extracted_questions folder

2. Use keyboard shortcuts to control the bot:

   | Shortcut | Action |
   |----------|--------|
   | `Ctrl+Alt+R` | Re-process the current page |
   | `Ctrl+Alt+Q` | Quit the application |

3. Find your saved solutions in the extracted_questions folder, organized by problem ID.

## Troubleshooting

- **Permission Denied Errors**: Try running the script as administrator, especially if keyboard shortcuts aren't working.
- **API Key Issues**: If you get API errors, check that your Gemini API key is valid and properly configured.
- **Element Not Found Errors**: Mathspace's HTML structure may change. If extraction fails, try updating the CSS selectors in the code.
- **Chrome Driver Issues**: If Chrome doesn't open, ensure you have the latest version of Chrome installed.

## How It Works

The bot uses:
- Selenium to control Chrome and navigate Mathspace
- Custom extraction logic to identify and parse math problems
- Google's Gemini API to solve the extracted problems
- File I/O to save results for later reference

## License

This project is for educational purposes only. Use responsibly and in accordance with Mathspace's terms of service.