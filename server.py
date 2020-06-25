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
import time
from datetime import timedelta

#algorithm to choose 
class Algoritmo():
    def __init__(self):
        self.workers = []
        self.c = 0

    def choose(self):
        worker = self.workers[self.c]
        self.c += 1
        if(self.c == len(self.workers)):
            self.c = 0
        return worker

#class to create server
class Server():
    def __init__(self, host, port, max_persons):
        self.flag = True
        self.start_time = 0
        self.temp = 0
        self.objects = {}
        self.workerNum = 0
        self.totalTime = 0
        self.contador = -1
        self.escalonamento = Algoritmo()
        self.global_port = 3456
        self.video_paths = []
        self.app = Flask(__name__)
        self.server_host = host
        self.server_port = port
        self.max_persons = max_persons
        self.worker_port = 0
        #app routing
        self.app.route('/', methods = ['POST'])(self.receiveFile)   
        self.app.route('/regist', methods = ['GET','POST'])(self.regist)    
        self.app.route('/image', methods = ['GET','POST'])(self.imageReceived)
        #run app  
        self.app.run(host = self.server_host, port = self.server_port, threaded=True)

    #receive file from client
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
            #add frame to array
            self.video_paths.append(nome)
        #Record total time
        self.start_time = time.time()
        #Iterate through all frames
        self.iterateFrames()
        return "Video delivered"

    def iterateFrames(self):
        #send n frames
        for x in self.escalonamento.workers:
            #If all frames were processed
            if(self.contador >= len(self.video_paths)):
                pass
            else:
                self.contador = self.contador + 1
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                future1 = loop.run_in_executor(None, self.requestFrame)
        return "OK"

    #send port to worker
    def regist(self):
        self.global_port = self.global_port + 1
        json_text = {'port': self.global_port}
        self.worker_port = self.global_port
        #append to workers array
        self.escalonamento.workers.append(("http://localhost:", str(self.global_port)))
        #send port to worker
        requests.post("http://" + self.server_host + ":" + str(self.server_port), json = json_text)
        return json_text

    #sends one frame to worker
    def requestFrame(self):
        frame_num = self.contador   #frame to send
        [worker_addr, worker_port] = self.escalonamento.choose()    #choose worker port to send
        worker_link = worker_addr + worker_port
        #start encoding frame in base64
        image_file = cv2.imread(self.video_paths[frame_num])
        image = base64.b64encode(cv2.imencode('.jpg', image_file)[1]).decode()
        json_text = {'image': image, 'frame': frame_num}   
        #send frame to worker
        requests.post(worker_link + "/receiveFrame", json = json_text)
        return "OK"

    #receive processed image
    def imageReceived(self):
        self.temp += 1
        #get parameters from worker
        r = request.json
        info = r["info"]
        time = r["enlapsed"]
        frame_num = r["frame"]
        self.totalTime = self.totalTime + time  #add total time to do average later
        self.workerNum += 1
        self.printAlert(info, frame_num)    #will print an alert if needed
        #if all frames were processed
        if(self.temp >= len(self.video_paths)):
                self.endProcessing()    #prints total stats
        else:
            if(self.workerNum == len(self.escalonamento.workers)):
                self.iterateFrames()
                self.workerNum = 0
        return "OK"
    
    #prints alert
    def printAlert(self, info, frame_num):
            person_counter = 0
            #calculate stats
            for obj in info:
                if(obj in self.objects.keys()):
                    self.objects[obj] += 1
                    if(obj == 'person'):
                        person_counter += 1
                else:
                    self.objects[obj] = 1
            #if number of people exceeds the defined
            if(person_counter > self.max_persons):
                print("Frame " + str(frame_num) + ": " + str(person_counter) + " <person> detected")
                person_counter=0
            
    #prints global stats
    def endProcessing(self):
        time.sleep(0.5)
        #to print only 1 time
        if(self.flag):
            self.flag = False
            print("Processed frames: " + str(self.temp))
            print("Average processing time per frame: " + "{:0>2.0f}".format(self.totalTime / (self.contador + 1)) + "ms")
            print("Person objects detected: " + str(self.objects['person']))
            print("Total classes detected: " + str(len(self.objects)))
            sortedArray = sorted(self.objects.items(), key=lambda x: x[1]) 
            print("Top 3 objects detected: " + sortedArray[len(sortedArray)-1][0] + ", " + sortedArray[len(sortedArray)-2][0] + ", " + sortedArray[len(sortedArray)-3][0])
            end = time.time() - self.start_time
            print("\nTempo de execução do video: " + str(timedelta(seconds=int("{:05.0f}".format(end)))))

#main
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", help="maximum number of persons in a frame", default=10)
    args = parser.parse_args()
    Server('localhost', 5000, int(args.max))