from model import efficientdet
import cv2
import os
import numpy as np
import time
from utils import preprocess_image, rotate_image
from utils.anchors import anchors_for_shape

os.environ['CUDA_VISIBLE_DEVICES'] = '1'

phi = 0
weighted_bifpn = True
model_path = 'checkpoints/2020-02-16/csv_21_0.4456_0.3596.h5'
image_sizes = (512, 640, 768, 896, 1024, 1280, 1408)
image_size = image_sizes[phi]
# classes = [
#     'aeroplane', 'bicycle', 'bird', 'boat', 'bottle', 'bus', 'car', 'cat', 'chair',
#     'cow', 'diningtable', 'dog', 'horse', 'motorbike', 'person', 'pottedplant', 'sheep', 'sofa', 'train', 'tvmonitor',
# ]
classes = ['vat']
num_classes = len(classes)
score_threshold = 0.5
colors = [np.random.randint(0, 256, 3).tolist() for i in range(num_classes)]
model, prediction_model = efficientdet(phi=phi,
                                       weighted_bifpn=weighted_bifpn,
                                       num_classes=num_classes,
                                       score_threshold=score_threshold)
prediction_model.load_weights(model_path, by_name=True)
###
# import tensorflow as tf
# import efficientnet
# import layers
# import initializers
# from utils import inject_tfkeras_modules
# import losses
# #
# prediction_model = tf.keras.models.load_model(
#     model_path,
#     custom_objects={
#         'BatchNormalization': layers.BatchNormalization,
#         'wBiFPNAdd': layers.wBiFPNAdd,
#         'PriorProbability': initializers.PriorProbability,
#         'swish': inject_tfkeras_modules(efficientnet.get_swish)(),
#         'FixedDropout': inject_tfkeras_modules(efficientnet.get_dropout)(),
#         '_smooth_l1': losses.smooth_l1(),
#         '_focal': losses.focal()
#     }
# )
###

import glob
for image_path in glob.glob('datasets/train_quad/ele/*.jpg'):
    image = cv2.imread(image_path)
    image = rotate_image(image)
    src_image = image.copy()
    image = image[:, :, ::-1]
    h, w = image.shape[:2]

    image, scale, offset_h, offset_w = preprocess_image(image, image_size=image_size)
    inputs = np.expand_dims(image, axis=0)
    anchors = anchors_for_shape((image_size, image_size))
    # run network
    start = time.time()
    boxes, scores, alphas, labels = prediction_model.predict_on_batch([np.expand_dims(image, axis=0),
                                                                       np.expand_dims(anchors, axis=0)])
    alphas = 1 / (1 + np.exp(-alphas))
    vertexes = np.zeros(boxes.shape[:2] + (8, ))
    vertexes[:, :, 0] = boxes[:, :, 0] + (boxes[:, :, 2] - boxes[:, :, 0]) * alphas[:, :, 0]
    vertexes[:, :, 1] = boxes[:, :, 1]
    vertexes[:, :, 2] = boxes[:, :, 2]
    vertexes[:, :, 3] = boxes[:, :, 1] + (boxes[:, :, 3] - boxes[:, :, 1]) * alphas[:, :, 1]
    vertexes[:, :, 4] = boxes[:, :, 2] - (boxes[:, :, 2] - boxes[:, :, 0]) * alphas[:, :, 2]
    vertexes[:, :, 5] = boxes[:, :, 3]
    vertexes[:, :, 6] = boxes[:, :, 0]
    vertexes[:, :, 7] = boxes[:, :, 3] - (boxes[:, :, 3] - boxes[:, :, 1]) * alphas[:, :, 3]
    print(time.time() - start)

    boxes[0, :, [0, 2]] = boxes[0, :, [0, 2]] - offset_w
    boxes[0, :, [1, 3]] = boxes[0, :, [1, 3]] - offset_h
    boxes /= scale
    boxes[0, :, 0] = np.clip(boxes[0, :, 0], 0, w - 1)
    boxes[0, :, 1] = np.clip(boxes[0, :, 1], 0, h - 1)
    boxes[0, :, 2] = np.clip(boxes[0, :, 2], 0, w - 1)
    boxes[0, :, 3] = np.clip(boxes[0, :, 3], 0, h - 1)

    vertexes[0, :, [0, 2, 4, 6]] = vertexes[0, :, [0, 2, 4, 6]] - offset_w
    vertexes[0, :, [1, 3, 5, 7]] = vertexes[0, :, [1, 3, 5, 7]] - offset_h
    vertexes /= scale
    vertexes[0, :, [0, 2, 4, 6]] = np.clip(vertexes[0, :, [0, 2, 4, 6]], 0, w - 1)
    vertexes[0, :, [1, 3, 5, 7]] = np.clip(vertexes[0, :, [1, 3, 5, 7]], 0, h - 1)

    # select indices which have a score above the threshold
    indices = np.where(scores[0, :] > score_threshold)[0]

    # select those detections
    boxes = boxes[0, indices]
    scores = scores[0, indices]
    labels = labels[0, indices]
    vertexes = vertexes[0, indices]

    for box, score, label, vertex in zip(boxes, scores, labels, vertexes):
        xmin = int(round(box[0]))
        ymin = int(round(box[1]))
        xmax = int(round(box[2]))
        ymax = int(round(box[3]))
        score = '{:.4f}'.format(score)
        class_id = int(label)
        color = colors[class_id]
        class_name = classes[class_id]
        label = '-'.join([class_name, score])
        ret, baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(src_image, (xmin, ymin), (xmax, ymax), color, 3)
        cv2.rectangle(src_image, (xmin, ymax - ret[1] - baseline), (xmin + ret[0], ymax), color, -1)
        cv2.putText(src_image, label, (xmin, ymax - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.drawContours(src_image, [vertex.astype(np.int32).reshape((4, 2))], -1, color, 3)
    cv2.namedWindow('image', cv2.WINDOW_NORMAL)
    cv2.imshow('image', src_image)
    cv2.waitKey(0)
