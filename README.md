# FitFinder

**Created:** March 20, 2025  
**Author:** Gerges Ibrahim

---

## Overview

FitFinder is a web service designed to enhance the online shopping experience by offering users a personalized catalog tailored to their measurements and preferences. The application leverages AWS Lambda functions for core functionalities such as user authentication, account creation, web scraping, and catalog management. The backend is powered by an RDS database and Amazon SQS for asynchronous processing.

---

## Features

### User Authentication & Authorization

- Sign in using either a token or username/password.
- Access tokens are generated with configurable expiration times.

### Account Creation

- Users can create accounts by providing:
  - **Username** and **password**
  - **Size measurements**, including:
    - **Top size:** XXS, XS, S, M, L, XL, XXL, 3XL
    - **Pants waist:** 24-50
    - **Pants length:** 26-40
    - **Shoe size:** 6-15 (half sizes accepted)
    - **Gender:** M, F, Other

### Catalog Viewing

- Authenticated users can view a personalized catalog curated based on their measurements and gender preferences.

### Web Scraping

- A dedicated Lambda function uses BeautifulSoup to scrape product data from ASOS catalogs.
- Handles infinite pagination until repeated items are detected.
- Scraped data includes product titles, prices, links, and additional details via secondary scraping.

### Task Polling

- Users can poll the status of long-running scraping tasks to monitor progress and receive updates.

---

## Setup Instructions

### Prerequisites

- Python 3.8+ (Ensure `pip3` is installed)
- AWS Account with credentials configured for AWS Lambda, RDS, and SQS
- Virtual environment (recommended for dependency isolation)

### Virtual Environment Setup

1. **Create a Virtual Environment**  
    Navigate to the project directory and run:
   ```bash
   python3 -m venv venv
   ```
2. **Activate the Virtual Environment**
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

### Installing Dependencies

With the virtual environment activated, install the required libraries:

```bash
pip3 install -r requirements.txt
```

---

## Configuration

### Client Configuration

Create or update the `fitfinder-client-config.ini` file with the following structure:

```ini
[client]
webservice = https://<your-api-gateway-url>
```

### AWS Configuration

Ensure the `fitfinder-config.ini` file is properly set up with your RDS and AWS configuration:

- RDS endpoint
- Port number
- Username
- Password
- Database name

---

## Usage

### Running the Client

Activate the virtual environment and run the client application:

```bash
python3 main.py
```

### Client Commands

The client provides the following options:

- **0:** End Service
- **1:** Log In
- **2:** Create an Account
- **3:** View Catalog
- **4:** Log Out
- **5:** Web Scrape (Developer tool)
- **6:** Poll Tasks

Follow the on-screen prompts to interact with the FitFinder service.

---

## Project Structure

### Lambda Functions

- **`auth`**: Handles authentication and token generation.
- **`make`**: Creates new user accounts.
- **`view`**: Retrieves personalized catalog items.
- **`scrape`**: Scrapes product data from ASOS catalogs.
- **`poll`**: Polls the status of long-running scraping tasks.

### Client Application

- **`main.py`**: Command-line client entry point.  
   Includes utility functions for interacting with the web service (GET and POST requests) and user prompts.

---

## Future Enhancements

- **Password Hashing**: Implement secure password hashing using libraries like `bcrypt` or `passlib`.
- **Enhanced Web Scraping**: Expand capabilities to handle lazy-loaded images and integrate additional fashion websites.
- **Improved Catalog & Database Design**: Develop a more sophisticated schema to manage item variants, images, sizes, and colors.
- **User Statistics & Account Management**: Add features for updating size preferences and viewing account statistics.

---

## Acknowledgements

- Original authorization logic adapted from work by Dilan Nair and Joseph Hummel.
- Special thanks to contributors and community members for their feedback during development.
