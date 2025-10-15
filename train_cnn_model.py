import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping

# Configuration
DATA_DIR = "card_data"
TRAIN_DIR = os.path.join(DATA_DIR, "train")
VALIDATION_DIR = os.path.join(DATA_DIR, "validation")
IMG_WIDTH, IMG_HEIGHT = 150, 150
BATCH_SIZE = 32
EPOCHS = 50
MODEL_SAVE_PATH = 'riftbound_card_recognition_model.h5'
CLASS_INDICES_PATH = 'cnn_class_indices.txt'

def build_model(num_classes):
    """Builds the Convolutional Neural Network model."""
    model = Sequential([
        # --- THIS IS THE KEY CHANGE ---
        # The input shape now expects 1 channel (grayscale)
        Conv2D(32, (3, 3), activation='relu', input_shape=(IMG_WIDTH, IMG_HEIGHT, 1)),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        
        Conv2D(64, (3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        
        Conv2D(128, (3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        
        Flatten(),
        Dense(512, activation='relu'),
        Dropout(0.5),
        Dense(num_classes, activation='softmax')
    ])
    
    model.compile(optimizer='adam',
                  loss='categorical_crossentropy',
                  metrics=['accuracy'])
    
    model.summary()
    return model

def train():
    """Trains the CNN model."""
    if not os.path.isdir(TRAIN_DIR):
        print(f"Error: Training directory '{TRAIN_DIR}' not found.")
        print("Please run the 'data_augmentor.py' script first.")
        return

    # --- THIS IS THE KEY CHANGE ---
    # We now tell the data generators to load all images as grayscale
    train_datagen = ImageDataGenerator(rescale=1./255)
    validation_datagen = ImageDataGenerator(rescale=1./255)

    train_generator = train_datagen.flow_from_directory(
        TRAIN_DIR,
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        color_mode='grayscale'  # <-- ADD THIS LINE
    )

    validation_generator = validation_datagen.flow_from_directory(
        VALIDATION_DIR,
        target_size=(IMG_WIDTH, IMG_HEIGHT),
        batch_size=BATCH_SIZE,
        class_mode='categorical',
        color_mode='grayscale'  # <-- ADD THIS LINE
    )
    
    num_classes = len(train_generator.class_indices)
    print(f"Found {num_classes} classes.")
    
    with open(CLASS_INDICES_PATH, 'w') as f:
        f.write(str(train_generator.class_indices))
    print(f"Class indices saved to '{CLASS_INDICES_PATH}'")
    
    model = build_model(num_classes)
    
    checkpoint = ModelCheckpoint(MODEL_SAVE_PATH, monitor='val_accuracy', verbose=1, save_best_only=True, mode='max')
    early_stopping = EarlyStopping(monitor='val_loss', patience=10, verbose=1, mode='min')
    
    callbacks_list = [checkpoint, early_stopping]
    
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=validation_generator,
        callbacks=callbacks_list
    )
    
    print("\nTraining complete! Best model saved to 'riftbound_card_recognition_model.h5'")

if __name__ == '__main__':
    train()