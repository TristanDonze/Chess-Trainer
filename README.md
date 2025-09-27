
## Getting Started

### Prerequisites
- Python 3.x
- Run `pip install -r requirements.txt` to install the required packages.
- To use stockfish, download the binary from [stockfishchess.org](https://stockfishchess.org/download/) and put the correct path in `backend/models/stockfish.py`.
- A modern web browser (e.g., Chrome, Firefox, Edge)
- .env at `backend/src/rag/.env` with the following variables:
    - WEAVIATE_REST_ENDPOINT=your_weaviate_instance
    - WEAVIATE_API_KEY=your_weaviate_api_key
    - OPENAI_API_KEY=your_openai_api_key

### Running the Project
1. Run backend:
    - Open a terminal at the root of the project
    - execute: `cd backend`
    - execute: `python server.py`

2. Run the frontend:
    - Open a terminal at the root of the project
    - execute: `cd frontend`
    - execute: `python -m http.server`

3. Open a browser and go to `http://localhost:8000/`
