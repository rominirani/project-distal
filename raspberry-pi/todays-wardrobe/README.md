# Project Distal 👗👔

A Python Flask application designed for the Raspberry Pi 5 that acts as your personal AI stylist. It checks your Google Calendar for today's events, analyzes the weather at those locations, and uses an advanced AI Stylist Agent to generate visual outfit recommendations for each event.

## Features

-   **📅 Smart Scheduling**: Connects to Google Calendar to fetch your agenda for the day.
-   **🌤️ Weather Aware**: Automatically checks the weather forecast for each event's location.
-   **🎨 AI Stylist**: Uses a custom AI Agent to suggest outfits based on the occasion, weather, and context.
-   **🖼️ Visual Ideas**: Generates visual representations of clothing items (Blouse, Pants, Shoes, etc.) per event.
-   **🖥️ Interactive UI**: A clean, responsive web interface tailored for the Raspberry Pi touch screen or any browser.
-   **📂 Item Metadata**: Displays details like material, color, and category for each recommended item.

---

## Prerequisites

-   **Hardware**: Raspberry Pi 5 (recommended) or any computer running Python 3.9+.
-   **Software**: Python 3.9+, pip.
-   **Accounts**:
    -   **Google Cloud Console**: For Google Calendar API credentials.
    -   *(Note: The Stylist AI is currently hosted on a public endpoint, so no internal LLM key is needed for that part, but you need internet access.)*

---

## Installation Guide

### 1. Clone the Repository
Open your terminal and clone this project and navigate to the `raspberry-pi/todays-wardrobe` folder.

### 2. Set Up Virtual Environment
It's best practice to use a virtual environment to manage dependencies:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it (Mac/Linux/Pi)
source venv/bin/activate
```

### 3. Install Dependencies
Install the required Python packages:

```bash
pip install -r requirements.txt
```

---

## Configuration

### 1. Google Calendar Credentials (`credentials.json`)
You need to generate a `credentials.json` file to allow the app to access your calendar.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project.
3.  Enable the **Google Calendar API**.
4.  Go to **Credentials** -> **Create Credentials** -> **OAuth client ID**.
5.  Choose **Desktop App**.
6.  Download the JSON file, rename it to `credentials.json`, and place it in the **root** of this project folder.

### 2. Environment Variables (`.env`)
Create a `.env` file in the root directory.

```bash
touch .env
```

Add the following variables (if applicable):

```env
# Optional: If you use any other API keys in the future
GEMINI_API_KEY=your_key_here 
```

*(Currently, the Stylist API endpoint is hardcoded, so this may not be strictly necessary for the core flow, but good practice.)*

---

## Running the Application

1.  Ensure your virtual environment is activated:
    ```bash
    source venv/bin/activate
    ```

2.  Run the Flask app:
    ```bash
    python3 app.py
    ```

3.  **On First Run**:
    -   A browser window (or link in the terminal) will open asking you to log in to Google.
    -   Authorize the app to view your Calendar.
    -   This will generate a `token.json` file.
    -   **Note for Headless Pi**: Perform this step on a desktop first, generate the `token.json`, and then copy that `token.json` file to your Raspberry Pi project folder.

4.  Open your browser and go to:
    ```
    http://localhost:5000
    ```

---

## Usage

1.  **Start**: Click the **"Suggest Wardrobe for the Day"** button on the homepage.
2.  **Wait**: The bar will progress as it:
    -   Fetches today's events.
    -   Checks weather for each location.
    -   Consults the AI Stylist.
    -   Downloads outfit images.
3.  **View**: Scroll down to see your personalized Fashion Agenda, with specific outfit cards for each event!

---

## Troubleshooting

-   **Token Expired**: If you get authentication errors, delete the `token.json` file and run the app again to re-authenticate.
-   **Images Not Showing**: Ensure the `static/` folder exists and is writable. The app saves downloaded images there.
-   **No Events**: The app defaults to a "General Day" recommendation if your calendar is empty.
