# Accessible Blackjack

This project is a Python application that makes the physical card game of Blackjack accessible to visually impaired users. It uses computer vision and text-to-speech (TTS) to act as a "sighted" assistant, audibly narrating the entire game as it's played on a real table.



## Core Features

* **Real-Time Card Recognition:** Uses a Roboflow-trained computer vision model to identify card ranks, suits, and their location on the table.
* **Text-to-Speech Feedback:** Announces all game events, totals, and results, providing a complete audio-based experience (e.g., "Cards dealt. You have 17," "Dealer busts with 24," "You win!").
* **100% Vision-Driven Logic:** This is the key innovation. The game requires **no keyboard, mouse, or voice commands.** The entire game flow is controlled by the dealer's physical actions.

## How it Works: The Vision-Driven Controls

The game logic infers the player's intent based *only* on what it sees with the camera.

1.  **To "Hit"**: The dealer places a new card in the **player's** zone.
    * **Result:** The game sees the new card, recalculates the player's total, and announces it (e.g., "Your total is now 19.").

2.  **To "Stand"**: The dealer places a new card in the **dealer's** zone.
    * **Result:** The game sees this as the signal to end the player's turn and begin the dealer's turn. It announces, "You stand with 19. Dealer's turn."

3.  **To "Play Again"**: The dealer clears all cards from the table.
    * **Result:** The game sees the empty table and automatically starts a new round, saying, "Table is clear. Please place 2 cards for yourself and 1 for the dealer."

## 💻 Technology Used

* **Python 3**
* **OpenCV:** For capturing the webcam feed.
* **Roboflow:** For the trained computer vision model.
* **macOS `say` command:** Used via `subprocess` for reliable, low-latency text-to-speech.
* **Pytest:** For unit testing the game logic.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/your-username/your-repository-name.git](https://github.com/your-username/your-repository-name.git)
    cd your-repository-name
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies:**
    (You must have a `requirements.txt` file for this to work)
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Game:**
    ```bash
    python blackjack_logic.py
    ```

## Project Structure

* **`blackjack_logic.py`**: The main application file. Runs the game loop and contains all the state machine logic.
* **`card_detection.py`**: Manages the webcam feed, loads the Roboflow model, and handles all card detection and spatial zone logic.
* **`tts_module.py`**: Manages the text-to-speech audio queue and speaking threads.
* **`test_blackjack_logic.py`**: Unit tests for the game logic, built with `pytest`.

# CNN Card Recognition Model

This module is the core of the card recognition system. It uses a Convolutional Neural Network (CNN) to identify playing cards from a processed image. The model is specifically trained to recognize cards from 150x150 pixel grayscale images.

## Dependencies

The primary dependencies for training and running the model are TensorFlow and OpenCV.

To install all necessary dependencies for this project, first activate your virtual environment, then run the following command:

```bash
pip3 install tensorflow opencv-python pyttsx3 SpeechRecognition pyaudio
```

## Training the Model

Training a new model is a multi-step process. You must have a collection of original card images to begin.

### Step 1: Populate the Raw Data Directory

The training process starts with a set of original images that you provide.

1.  Create a directory named `raw_cards` in the project's root folder if it doesn't exist.
2.  Inside `raw_cards`, create a separate folder for each card you want to train. The folder name is important, as it will become the label for the card (e.g., `A_spades`, `K_hearts`, `7_clubs`).
3.  Place at least **15-20 unique photos** of the corresponding card into each folder. More images with varied lighting and angles will result in a more accurate model.

The final directory structure should look like this:

```
RiftboundForAll/
├── raw_cards/
│   ├── 2_hearts/
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   ├── K_spades/
│   │   ├── image1.jpg
│   │   └── image2.jpg
│   └── ... (and so on for all cards)
├── data_augmentor.py
└── train_cnn_model.py
```

### Step 2: Generate the Augmented Dataset

The `data_augmentor.py` script takes your original images and creates a large, varied dataset for training. It reads from `raw_cards`, applies random rotations, shifts, and brightness changes, and saves the new images to a `card_data` directory.

To run it, first activate your virtual environment, then execute the script:

```bash
# First, activate the environment
source env/bin/activate

# Then, run the data augmentor
python3 data_augmentor.py
```

### Step 3: Run the Training Script

This is the main step that builds and trains the CNN. The `train_cnn_model.py` script will:
* Load the augmented images from the `card_data` directory.
* Build the CNN model architecture.
* Train the model for a set number of epochs (or until it stops improving).
* Save the best-performing model to a file.

To start training, run the following command:

```bash
python3 train_cnn_model.py
```
**Note:** This process is computationally intensive and can take a very long time, especially without a dedicated GPU.

### Step 4: Use the Trained Model

The training process outputs two files that are essential for the main application:

1.  `riftbound_card_recognition_model.h5`: The saved, trained neural network.
2.  `cnn_class_indices.txt`: A text file mapping the card names to the model's output indices.

These files are automatically loaded by the `CNNRecognitionModule` when you run `modular_blackjack_system.py`, allowing the application to make live predictions.

# Accessible Blackjack System

A modular, voice-controlled blackjack game designed for blind and visually impaired users.

# User Interface for Blackjack System
- Start the Python program (it will open the camera and start TTS)
- Open your browser and go to: http://localhost:5001
- You'll see the modern UI with real-time connection to your Python backend

## Features
- Voice-controlled interface
- Computer vision card detection  
- Template-based card recognition
- Template training system
- Complete blackjack game logic

## Quick Start
1. Run: `install_script.py`
2. Run: `accessible_blackjack.py`
3. Say "train templates" to add card recognition templates
4. Say "play blackjack" to start playing

## File Structure
- `accessible_blackjack.py` - Main system coordinator
- `simple_card_detector.py` - Card database and template recognition  
- `install_script.py` - Downloading necesarry libraries and testing
- `card_database/` - Directory for card templates and data
- `test_components.py` - Testing all components


## Voice Commands

### Main Menu
- "blackjack" - Start game
- "help" - Show commands
- "quit" - Exit

### During Game  
- "detect cards" - Check card recognition
- "deal" - Start with current cards
- "hit" - Take another card
- "stand" - Stop taking cards
- "new game" - Reset game

## Setup Tips
- Use dark background for cards
- Ensure bright, even lighting
- Keep cards flat and separate
- Position camera 12-18 inches above cards
