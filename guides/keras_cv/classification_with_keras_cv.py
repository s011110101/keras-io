# Copyright 2022 The KerasCV Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Title: Classification with KerasCV
Author: [lukewood](https://lukewood.xyz)
Date created: 03/28/2023
Last modified: 03/28/2023
Description: Use KerasCV to train a state of the art image classifier.
"""

"""
KerasCV is a computer vision library that supports users through their entire
development cycle.
Our workflows are built from modular components that have state-of-the-art
preset weights and architectures when used out-of-the-box and are easily
customizable when more control is needed. We emphasize building APIs that are
user-friendly, yet still yield state of the art results.
Due to the in-graph nature of our models, users can expect easy
productionization using the TensorFlow ecosystem.

This library is an extension of the core Keras API; all high-level modules are
Layers or Models. If you are familiar with Keras, congratulations! You already
understand most of KerasCV.

This guide demonstrates our modular approach using an image classification
example at two levels of complexity:

- Inference with a pretrained classifier
- Fine tuning a pretrained backbone

We use Professor Keras, the official Keras mascot, as a
visual reference for the complexity of the material:

![](https://storage.googleapis.com/keras-nlp/getting_started_guide/prof_keras_evolution.png)

Please note that due to classification being a pretty simple use case, this guide only covers beginner and intermediate work flows.
Advanced and expert workflows may be found in the [other KerasCV guides](https://keras.io/guides/keras_cv/)!
"""

"""shell
!pip install -q --upgrade git+https://github.com/keras-team/keras-cv.git tensorflow
"""

import json
import keras_cv
import tensorflow as tf
import tensorflow_datasets as tfds
import keras
import numpy as np

"""
## Inference with a pretrained classifier

![](https://storage.googleapis.com/keras-nlp/getting_started_guide/prof_keras_beginner.png)

Let's get started with the simples KerasCV API: a pretrained classifier.
In this example we will build a Dogs vs Cats classifier using a model that was
pretrained on the ImageNet dataset.

The highest level module in KerasCV is a *task*. A *task* is a `keras.Model`
consisting of a (generally pretrained) backbone model and task-specific layers.
Here's an example using keras_cv.models.ImageClassifier with a ResNet50V2
Backbone.


"""

import json
import keras_cv
import tensorflow as tf
import tensorflow_datasets as tfds
import keras
import numpy as np

# TODO(lukewood): replace with ImageClassifier.from_preset()
classifier = keras_cv.models.DenseNet121(
    weights='imagenet',
    include_top=True,
    include_rescaling=True,
    num_classes=1000
)

filepath = tf.keras.utils.get_file(origin="https://i.imgur.com/9i63gLN.jpg")
image = keras.utils.load_img(filepath)
image

image = np.array(image)

predictions = classifier.predict(image[None, ...])
top_classes = predictions[0].argsort(axis=-1)

# Subset of imagenet classes
classes = {
    281: 'tabby, tabby cat',
    885: 'velvet'
}
top_two = [classes[i] for i in top_classes[-2:]]
print("Top two classes are:", top_two)

"""Great!  Both of these are correct!  But what if you don't care about the
velvet blanket, and instead only want to know if a cat is in the image or not?
This can be solved using fine tuning.

# Fine tuning a pretrained classifier

![](https://storage.googleapis.com/keras-nlp/getting_started_guide/prof_keras_intermediate.png)

When labeled images specific to our task are available, fine-tuning a custom
classifier can improve performance. If we want to train a Cats VS Dogs
Classifier, using explicitly labeled Cat vs Dog data should perform better than
the generic classifier data! And for many tasks, no relevant pretrained model
will be available (e.g., categorizing images specific to your application).

The biggest difficulty when finetuning a KerasCV model is loading and augmenting
your data.  Luckily, we've handled the second half for you, so all you'll have
to do is load your own data.

First, let's setup our data pipeline:
"""

BATCH_SIZE = 32
AUTOTUNE = tf.data.AUTOTUNE
tfds.disable_progress_bar()

data, dataset_info = tfds.load("cats_vs_dogs", with_info=True, as_supervised=True)
train_steps_per_epoch = dataset_info.splits["train"].num_examples // BATCH_SIZE
train_dataset = data['train']

IMAGE_SIZE = (224, 224)
num_classes = dataset_info.features["label"].num_classes

random_crop = keras_cv.layers.Resizing(224, 224, crop_to_aspect_ratio=True)

def package_dict(image, label):
    image = tf.cast(image, tf.float32)
    image = random_crop(image)
    label = tf.one_hot(label, num_classes)
    return {"images": image, "labels": label}


train_dataset = train_dataset.shuffle(10 * BATCH_SIZE).map(package_dict, num_parallel_calls=AUTOTUNE)
train_dataset = train_dataset.batch(BATCH_SIZE)

images = next(iter(train_dataset.take(1)))['images']
keras_cv.visualization.plot_image_gallery(images, value_range=(0, 255))

"""
Next, lets assemble a `keras_cv` augmentation pipeline.
In this guide, we use the standard pipeline
[CutMix, MixUp, and RandAugment](https://keras.io/guides/keras_cv/cut_mix_mix_up_and_rand_augment/)
augmentation pipeline.  More information on the behavior of these augmentations
may be found in their
[corresponding Keras.io guide](https://keras.io/guides/keras_cv/cut_mix_mix_up_and_rand_augment/).
"""

augmenter = keras.Sequential(
    layers=[
        keras_cv.layers.RandomFlip(),
        keras_cv.layers.RandAugment(value_range=(0, 255)),
        keras_cv.layers.CutMix(),
        keras_cv.layers.MixUp()
    ]
)

train_dataset = train_dataset.map(augmenter, num_parallel_calls=tf.data.AUTOTUNE)

images = next(iter(train_dataset.take(1)))['images']
keras_cv.visualization.plot_image_gallery(images, value_range=(0, 255))

"""
Next let's construct our model:
"""

backbone = keras_cv.models.DenseNet121(
    include_rescaling=True,
    include_top=False,
    num_classes=2,
    pooling='max',
    weights="imagenet/classification"
)
model = keras.Sequential(
    [backbone, keras.layers.Dense(2, activation='softmax')]
)
model.compile(
    loss='categorical_crossentropy',
    optimizer=tf.optimizers.SGD(learning_rate=0.01),
    metrics=['accuracy'],
)

"""
All that is left to do is construct a standard Keras `model.fit()` loop!
"""

def unpackage_data(inputs):
  return inputs['images'], inputs['labels']

train_dataset.map(unpackage_data, num_parallel_calls=tf.data.AUTOTUNE)
train_dataset = train_dataset.prefetch(tf.data.AUTOTUNE)

model.fit(train_dataset.map(unpackage_data, num_parallel_calls=tf.data.AUTOTUNE))

predictions = model.predict(image[None, ...])

classes = {
    0: 'cat',
    1: 'dog'
}
print("Top class is:", classes[predictions[0].argmax()])

"""
## Conclusions

KerasCV makes producing robust solutions to classification problems easy.
Making use of the KerasCV `ImageClassifier` API, pretrained weights, and the
KerasCV data augmentations allows you to train a powerful classifier in `<50`
lines of code.

As a follow up exercise, give the following a try:

- Fine tune a KerasCV classifier on your own dataset
- Learn more about [KerasCV's data augmentations](https://keras.io/guides/keras_cv/cut_mix_mix_up_and_rand_augment/)
- Check out how we train our models on [ImageNet](https://github.com/keras-team/keras-cv/blob/master/examples/training/classification/imagenet/basic_training.py)
"""