import argparse
from flask import Flask, request, jsonify
import requests
import json
import video2image
import cv2
import base64
import numpy as np

class RoundRobin():
    def __init__(self):
        self.workers = []
        self.c = 0

    def choose(self):
        worker = self.workers[self.c]
        self.c += 1
        if(self.c == len(self.workers)):
            print(len(self.workers))
            self.c = 0
        return worker


class Server():
    def __init__(self, host, port, max_persons):
        self.escalonamento = RoundRobin()
        self.global_port = 3456
        self.workers_pool = []
        self.processing = {}
        self.video_paths = []
        self.app = Flask(__name__)
        self.server_host = host
        self.server_port = port
        self.max_persons = max_persons
        self.worker_port = 0
        self.app.route('/', methods = ['POST'])(self.receiveFile)
        self.app.route('/regist', methods = ['GET','POST'])(self.regist)
        self.app.route('/image', methods = ['GET','POST'])(self.imageReceived)
        self.app.run(host = self.server_host, port = self.server_port, threaded=True)

    def receiveFile(self):
        file = request.files['video']
        file.save(file.filename)
        self.upload_file(file.filename)
        return "Video delivered"
        
    def upload_file(self, filename):
        vidcap = cv2.VideoCapture(filename)
        success,image = vidcap.read()
        count = 0
        while success:
            nome = "frame" + str(count) + ".jpg"
            cv2.imwrite("frame%d.jpg" % count, image)     # save frame as JPEG file
            success,image = vidcap.read()
            print ('Read a new frame: ', success)
            count += 1
            self.video_paths.append(nome)
            #if(len(self.workers_pool > 0)):
                #self.requestFrame(self.video_paths[0])
        self.iterateFrames()
        return "Video delivered."

    def iterateFrames(self):
        for frame in self.video_paths:
            print("requested")
            self.requestFrame(frame)
        return "OK"

    def regist(self):
        self.global_port = self.global_port + 1
        json_text = {'port': self.global_port}
        self.worker_port = self.global_port
        self.escalonamento.workers.append(("http://localhost:", str(self.global_port)))
        print("WORKER COM PORTA: " + str(self.global_port))
        requests.post("http://" + self.server_host + ":" + str(self.server_port), json = json_text)
        
        return json_text


    def requestFrame(self, frame):
        [worker_addr, worker_port] = self.escalonamento.choose()
        worker_link = worker_addr + worker_port
        self.processing[worker_port] = frame
        print(worker_link)
        image_file = cv2.imread(frame)
        image = base64.b64encode(cv2.imencode('.jpg', image_file)[1]).decode()
        imagem2 = base64.b64decode(image)

        json_text = {'image': image, 'teste': "teste de uma string"}
        requests.post(worker_link + "/requestFrame", json = json_text)
        return "OK"

    def imageReceived(self):
        r = request.json
        info = r["info"]
        time = r["enlapsed"]
        print(info)
        print(time)
        return "OK"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", help="maximum number of persons in a frame", default=10)
    args = parser.parse_args()
    Server('localhost', 5000, args.max)