
## Getting Started

### Prerequisites
- Python 3.x
- Saves of the models weights [download here](https://drive.google.com/drive/folders/16BpdM9m3fjv0AL2a3xypOePxatA4-IMQ?usp=sharing). Place the folder `saves` in backend/models (such as backend/models/saves/...pth)
- Run `pip install -r requirements.txt` to install the required packages.
- To use stockfish, download the binary from [stockfishchess.org](https://stockfishchess.org/download/) and put the correct path in `backend/models/stockfish.py`.

### Running the Project
1. Run backend:
    - Open a terminal at the root of the project
    - execute: `cd backend`
    - execute: `python server.py`

2. Run the frontend: 
    - Open a terminal at the root of the projecvt
    - execute: `cd frontend`
    - execute: `python -m http.server`

3. Open a browser and go to `http://localhost:8000/`
