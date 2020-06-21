import argparse
import requests
import json
from flask import Flask, request, jsonify
import object_detect
import base64
import numpy as np
import cv2
import sys
import core.utils as utils
import tensorflow as tf
from core.yolov3 import YOLOv3, decode
from core.config import cfg
from PIL import Image
import time

class Worker():
    def __init__(self, address, port):
        self.server_address = address
        self.server_port = port
        self.app = Flask(__name__)
        self.worker_port = 0
        self.image_details = []
        self.bbox_tensors = []
         # Setup tensorflow, keras and YOLOv3
        self.input_size   = 416
        self.input_layer  = tf.keras.layers.Input([self.input_size, self.input_size, 3])
        self.feature_maps = YOLOv3(self.input_layer)
        for i, fm in enumerate(self.feature_maps):
            bbox_tensor = decode(fm, i)
            self.bbox_tensors.append(bbox_tensor)
        self.model = tf.keras.Model(self.input_layer, self.bbox_tensors)
        utils.load_weights(self.model, "./yolov3.weights")
        self.app.route('/requestFrame', methods = ['POST','GET'])(self.requestFrame)
        self.main()
        

    def main(self):
        r = requests.get("http://" + self.server_address + ":" + str(self.server_port) + "/regist")
        json_text = r.json()
        self.worker_port = json_text["port"]
        self.app.run(port=self.worker_port)
        
    
    def requestFrame(self):
        r = request.json
        imagem = r["image"]
        imagem2 = base64.b64decode(imagem)
        jpg_as_np = np.frombuffer(imagem2, dtype=np.uint8)
        img = cv2.imdecode(jpg_as_np, flags=1)
        
        self.image_details, exec_time = self.calculate(img)
        self.sendImageInfo(exec_time)
        return "OK"
    
    def sendImageInfo(self, exec_time):
        json_text = {'info': self.image_details, 'enlapsed' : exec_time}
        requests.post("http://" + self.server_address + ":" + str(self.server_port) + "/image", json = json_text)
        return "OK"

    def calculate(self, frame):
        time.sleep(5)
        start = int(round(time.time() * 1000))
        # Image to be processed
        original_image = frame #you can and should replace this line to receive the image directly (not from a file)
        # Read class names
        class_names = {}
        with open(cfg.YOLO.CLASSES, 'r') as data:
            for ID, name in enumerate(data):
                class_names[ID] = name.strip('\n')

       

        original_image      = cv2.cvtColor(original_image, cv2.COLOR_BGR2RGB)
        original_image_size = original_image.shape[:2]

        image_data = utils.image_preporcess(np.copy(original_image), [self.input_size, self.input_size])
        image_data = image_data[np.newaxis, ...].astype(np.float32)

        
        

        

        pred_bbox = self.model.predict(image_data)
        pred_bbox = [tf.reshape(x, (-1, tf.shape(x)[-1])) for x in pred_bbox]
        pred_bbox = tf.concat(pred_bbox, axis=0)

        bboxes = utils.postprocess_boxes(pred_bbox, original_image_size, self.input_size, 0.3)
        bboxes = utils.nms(bboxes, 0.45, method='nms')

        # We have our objects detected and boxed, lets move the class name into a list
        objects_detected = []
        for x0,y0,x1,y1,prob,class_id in bboxes:
            objects_detected.append(class_names[class_id])

        # Lets show the user a nice picture - should be erased in production
        #image = utils.draw_bbox(original_image, bboxes)
        #image = Image.fromarray(image)
        #image.show()
        exec_time = int(round(time.time() * 1000)) - start
        print(f"Objects Detected: {objects_detected}")
        return objects_detected, exec_time


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-address", help="server address", default="localhost")
    parser.add_argument("--server-port", help="server address port", default=5000)
    args = parser.parse_args()
    #main(args.server_address, args.server_port)
    Worker(args.server_address, args.server_port)