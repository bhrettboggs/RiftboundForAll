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
