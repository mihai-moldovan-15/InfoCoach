# AI Chatbot with Feedback System

A Flask-based web application that provides an interactive chatbot interface with feedback collection capabilities. The application supports multiple AI models and stores user feedback in a SQLite database.

## Features

- Interactive chat interface
- Support for multiple AI models (OpenAI, Anthropic, Google)
- Feedback collection system
- SQLite database for storing feedback
- Environment variable configuration
- Modern and responsive UI

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- SQLite3

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
# On Windows
.venv\Scripts\activate
# On Unix or MacOS
source .venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with your API keys:
```
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
```

## Project Structure

```
.
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── feedback/          # Feedback database directory
├── resources/         # Static resources
└── templates/         # HTML templates
```

## Running the Application

1. Make sure your virtual environment is activated
2. Run the Flask application:
```bash
python app.py
```
3. Open your web browser and navigate to `http://localhost:5000`

## Usage

1. Select your preferred AI model from the dropdown menu
2. Type your message in the chat input field
3. Press Enter or click the send button to get a response
4. Provide feedback on the responses using the feedback buttons
5. View feedback statistics in the feedback section

## Database

The application uses SQLite to store feedback data. The database file is automatically created in the `feedback` directory when you first run the application.

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support, please open an issue in the repository or contact the maintainers. 