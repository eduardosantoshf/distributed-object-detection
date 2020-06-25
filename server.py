import argparse
from flask import Flask, request, jsonify
import requests
import json
import video2image
import cv2
import base64
import numpy as np
import threading
import asyncio
import functools
import concurrent.futures

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
        self.temp = 0
        self.objects = {}
        self.workerNum = 0
        self.totalTime = 0
        self.contador = -1
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
        for x in self.escalonamento.workers:
            if(self.contador >= len(self.video_paths)):
                pass
            else:
                self.contador = self.contador + 1
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                future1 = loop.run_in_executor(None, self.requestFrame)
            #self.requestFrame
        return "OK"

    def regist(self):
        self.global_port = self.global_port + 1
        json_text = {'port': self.global_port}
        self.worker_port = self.global_port
        self.escalonamento.workers.append(("http://localhost:", str(self.global_port)))
        print("WORKER COM PORTA: " + str(self.global_port))
        requests.post("http://" + self.server_host + ":" + str(self.server_port), json = json_text)
        
        return json_text


    def requestFrame(self):
        #print("requested")
        [worker_addr, worker_port] = self.escalonamento.choose()
        worker_link = worker_addr + worker_port
        self.processing[worker_port] = self.video_paths[self.contador]
        #print(worker_link)
        image_file = cv2.imread(self.video_paths[self.contador])
        image = base64.b64encode(cv2.imencode('.jpg', image_file)[1]).decode()
        imagem2 = base64.b64decode(image)

        json_text = {'image': image}
        requests.post(worker_link + "/requestFrame", json = json_text)
        
        return "OK"

    def imageReceived(self):
        self.temp += 1
        r = request.json
        info = r["info"]
        time = r["enlapsed"]
        self.totalTime = self.totalTime + time
        
        #print(info)
        #print(self.timeArray[len(self.timeArray-2)])
        #print(time - self.timeArray[len(self.timeArray)-2])
        self.workerNum += 1

        self.printAlert(info)

        if(self.workerNum == len(self.escalonamento.workers)):
            self.iterateFrames()
            self.workerNum = 0
        
        print(self.contador)
        print(len(self.video_paths))
        if(self.contador >= len(self.video_paths)):
            self.endProcessing()

        return "OK"
    
    def printAlert(self, info):
            person_counter = 0
            for obj in info:
                if(obj in self.objects.keys()):
                    self.objects[obj] += 1
                    if(obj == 'person'):
                        person_counter += 1
                else:
                    self.objects[obj] = 1
            if(person_counter > self.max_persons):
                print("Frame " + str(self.temp) + ": " + str(person_counter) + " <person> detected")
                person_counter=0
            

    
    def endProcessing(self):
        print("Processed frames: " + str(self.contador))
        print("Average processing time per frame: " + str(self.totalTime / (self.contador + 1)))
        print("Person objects detected: " + str(self.objects['person']))
        print("Total classes detected: " + str(len(self.objects)))

        sortedArray = sorted(self.objects.items(), key=lambda x: x[1]) 
        print("Top 3 objects detected: " + sortedArray[len(sortedArray)-1][0] + ", " + sortedArray[len(sortedArray)-2][0] + ", " + sortedArray[len(sortedArray)-3][0])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", help="maximum number of persons in a frame", default=10)
    args = parser.parse_args()
    Server('localhost', 5000, int(args.max))