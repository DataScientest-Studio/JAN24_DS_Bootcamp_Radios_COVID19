# -*- coding: utf-8 -*-
"""VGG19_entrainement.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1r_XPKBbdiXhFt7_0mLMzciRoJMhLQCbm

Installation de Keras Tuner
"""

!pip install keras-tuner

"""Importations"""

from google.colab import drive
import pickle
import os
import numpy as np
import pandas as pd
import seaborn as sns
import cv2
from IPython.display import Image, display
import json
import matplotlib.pyplot as plt
import keras
import tensorflow as tf


from keras import regularizers
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix
from tensorflow.keras.applications.vgg19 import VGG19, preprocess_input
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout, Flatten
from tensorflow.keras.models import Model, Sequential, load_model
from tensorflow.keras.optimizers import SGD, Adam
from tensorflow.keras.callbacks import TensorBoard, EarlyStopping
from tensorflow.keras.preprocessing.image import ImageDataGenerator, load_img, img_to_array
from tensorflow.keras.regularizers import l2, l1
from tensorflow.keras.losses import BinaryCrossentropy
from tensorflow.keras.metrics import Accuracy
from kerastuner.tuners import RandomSearch

"""Montage de Google Drive"""

drive.mount('/content/drive')

"""Prétraitement des images pour VGG19, étiquetage, division des données en ensembles d'entraînement et de test pour la classification d'images."""

# Fonction pour redimensionner, normaliser et prétraiter une image pour VGG19
def preprocess_image_vgg(img_path, target_size=(224, 224)):
    # Charger l'image depuis le chemin du fichier en couleur
    img = cv2.imread(img_path)
    # Redimensionner l'image à la taille cible pour VGG19
    img_resized = cv2.resize(img, target_size)
    # Prétraiter l'image pour VGG19
    img_preprocessed = preprocess_input(img_resized)
    return img_preprocessed

# Chemin vers vos dossiers contenant les images saines et malades
sain_folder_path = "/content/drive/MyDrive/Test_Modelo/Sain"
malade_folder_path = "/content/drive/MyDrive/Test_Modelo/Malade"

# Liste pour stocker les données d'images et les étiquettes
images_data = []
labels = []

# Parcourez le dossier contenant les images saines
for filename in os.listdir(sain_folder_path):
    # Construire le chemin complet de l'image
    img_path = os.path.join(sain_folder_path, filename)
    # Prétraiter l'image pour VGG16 et l'ajouter à la liste des données d'images
    images_data.append(preprocess_image_vgg(img_path))
    # Étiquettez les images saines comme 0
    labels.append(0)

# Parcourez le dossier contenant les images malades
for filename in os.listdir(malade_folder_path):
    # Construire le chemin complet de l'image
    img_path = os.path.join(malade_folder_path, filename)
    # Prétraiter l'image pour VGG19 et l'ajouter à la liste des données d'images
    images_data.append(preprocess_image_vgg(img_path))
    # Étiquettez les images malades comme 1
    labels.append(1)

# Convertissez les listes en tableaux numpy
images_data = np.array(images_data)
labels = np.array(labels)

# Divisez vos données en ensembles d'entraînement et de test
x_train, x_val, y_train, y_val = train_test_split(images_data, labels, test_size=0.2, random_state=42)

"""Construction du modèle avec Keras Tuner, recherche des hyperparamètres, compilation et validation."""

# Définition de la fonction de construction de modèle pour Keras Tuner
def build_model(hp):
    # Hyperparamètres à rechercher
    learning_rate = hp.Choice('learning_rate', values=[1e-2, 1e-3, 1e-4])
    units = hp.Int('units', min_value=32, max_value=512, step=32)
    dropout_rate = hp.Float('dropout_rate', min_value=0.0, max_value=0.5, step=0.1)
    l2_lambda = hp.Choice('l2_lambda', values=[1e-3, 1e-4, 1e-5])

    # Chargement du modèle VGG19 pré-entraîné
    base_model = VGG19(weights='imagenet', include_top=False, input_shape=(224, 224, 3))

    # Dégel des dernières couches de convolution
    for layer in base_model.layers:
        if 'block5' in layer.name:
            layer.trainable = True
        else:
            layer.trainable = False

    # Ajout des couches fully-connected
    x = GlobalAveragePooling2D()(base_model.output)
    x = Dense(units, activation='relu', kernel_regularizer=regularizers.l2(l2_lambda))(x)
    x = Dropout(dropout_rate)(x)
    output = Dense(1, activation='sigmoid')(x)

    # Création du modèle final
    model = Model(inputs=base_model.input, outputs=output)

    # Compilation du modèle avec les hyperparamètres
    model.compile(optimizer=Adam(learning_rate=learning_rate),
                  loss='binary_crossentropy',
                  metrics=['accuracy'])

    return model

# Configuration du tuner d'hyperparamètres
tuner = RandomSearch(
    build_model,
    objective='val_accuracy',
    max_trials=1,
    directory='dir8',
    project_name='vgg19_dropout_regularization'
)

# Recherche des hyperparamètres
tuner.search(x_train, y_train,
             epochs=5, batch_size=16, validation_split=0.2,
             validation_data=(x_val, y_val))

"""Obtention des meilleurs hyperparamètres et construction du modèle correspondant avec Keras Tuner."""

# Récupérer les meilleurs hyperparamètres
best_hp = tuner.get_best_hyperparameters()[0]

# Construire le modèle avec les meilleurs hyperparamètres trouvés
best_model = tuner.hypermodel.build(best_hp)

"""Affichage des valeurs des meilleurs hyperparamètres trouvés par Keras Tuner et entraînement du modèle avec les meilleurs hyperparamètres trouvés."""

print(best_hp.values)

# Entraîner le modèle avec les meilleurs hyperparamètres trouvés
history = best_model.fit(x_train, y_train,
                         epochs=5,batch_size=16,
                         validation_data=(x_val, y_val))

# Afficher l'accuracy et la perte en fonction du nombre d'époques
plt.plot(history.history['accuracy'], label='Train Accuracy')
plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
plt.xlabel('Epochs')
plt.ylabel('Accuracy')
plt.title('Train and Validation Accuracy')
plt.legend()
plt.show()

plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.title('Train and Validation Loss')
plt.legend()
plt.show()

# Enregistrer le modèle
best_model.save('/content/drive/MyDrive/models/VGG19_finetuned_model.h5')

# Enregistrer l'historique
with open('/content/drive/MyDrive/models/VGG19_finetuned_history.pkl', 'wb') as file:
    pickle.dump(history.history, file)

# Enregistrer les métriques dans un fichier JSON
metrics_dict = {
    'loss': history.history['loss'],
    'accuracy': history.history['accuracy'],
    'val_loss': history.history['val_loss'],
    'val_accuracy': history.history['val_accuracy']
}

with open('/content/drive/MyDrive/models/VGG19_finetuned_metrics.json', 'w') as json_file:
    json.dump(metrics_dict, json_file)