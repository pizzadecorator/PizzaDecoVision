from imutils import face_utils
import numpy as np
import imutils
import dlib
import cv2
import math
import time
import serial
#from multiprocessing import Process, Queue, Manager,Pipe
#import multiprocessing
from threading import Thread
from queue import Queue

'''
Referenced by : https://www.pyimagesearch.com/2017/04/10/detect-eyes-nose-lips-jaw-dlib-opencv-python/

Links for dlib : https://pypi.org/simple/dlib/
In windows: you have to download dlib-19.8.1-cp36-cp36m-win_amd64.whl to your workspace
and command 'pip install dlib-19.8.1-cp36-cp36m-win_amd64.whl'

Another prerequisite : 'pip install imutils'

'''

class EyeDetectingWorker(Thread):

	def __init__(self, worker_id, img_queue, result_queue, resolution):
		Thread.__init__(self)
		self.id = worker_id
		self.img_queue = img_queue
		self.result_queue = result_queue
		self.resolution = resolution 

	def run(self):
		width, height = self.resolution
		detector = dlib.get_frontal_face_detector()
		predictor = dlib.shape_predictor('./shape_predictor_68_face_landmarks.dat')
		while True:
			if not self.img_queue.empty():
				# print("Thread " + str(self.id) + " work!!")
				img = self.img_queue.get()
				gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
				rects = detector(gray, 1)
				rects = [rect for rect in rects if ((width / 2) - rect.center().x) ** 2 + ((height / 2) - rect.center().y) ** 2 < (height / 3)**2]
				rects = sorted(rects, key=lambda rect: rect.area(), reverse=True)
		
				if len(rects) == 0:
					continue

				shape = predictor(gray, rects[0])
				indicators = face_utils.shape_to_np(shape)
				left = np.mean(indicators[36:42], axis=0).astype(int)
				right = np.mean(indicators[42:48], axis=0).astype(int)
				self.result_queue.put((left, right))

if __name__ == '__main__':

	'''
	' code for serial communication with arduino board
	'''


	ser = serial.Serial('COM4', 115200)

	if ser.isOpen(): 
		ser.close()
	ser.open()

	cap = cv2.VideoCapture(1)
	cap.set(cv2.CAP_PROP_FPS, 60)
	cap.set(cv2.CAP_PROP_FRAME_WIDTH, 400)
	cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 300)
	resolution = (cap.get(cv2.CAP_PROP_FRAME_WIDTH), cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
	img_queue = Queue(maxsize=20)
	result_queue = Queue(maxsize=20)

	NUM_WORKER = 8

	workers = []

	for worker_id in range(NUM_WORKER):
		worker = EyeDetectingWorker(worker_id, img_queue, result_queue, resolution)
		workers.append(worker)
		worker.daemon = True
		worker.start()

	frame_id = 0
	left, right = (None, None)
	angle_prev = 0
	while True:
		# Grab a single frame of video
		ret, img = cap.read()
		frame_id = frame_id + 1

		if not img_queue.full():
			img_queue.put(img)

		#print(result_queue.qsize())
		while not result_queue.empty():
			left, right = result_queue.get()
			angle = int(math.atan((right[1] - left[1]) / (right[0] - left[0])) * 180 / math.pi)
			print("Current angle is : " + str(angle))
			if(abs(angle_prev)-15)*(abs(angle)-15) <= 0:
				ser.write(str(angle).encode('ascii'))
				ser.write(b'\n')
			angle_prev = angle
			#print(chr(ser.read()))
		
		if ser.in_waiting:
			print("RESPONSE: " + str(ser.readline()))

		#motor_angle = ser.read_until('\n')
	#	print(motor_angle)

		if left is not None and right is not None:
			cv2.line(img, tuple(left), tuple(right), (255, 0, 0), 3)

		cv2.imshow('recc', img)

		if cv2.waitKey(1) & 0xFF == ord('q'):
			cap.release()
			cv2.destroyAllWindows()
			break

		if (cv2.waitKey(1) & 0xFF == ord('w')) or (cv2.waitKey(1) & 0xFF == ord('e')):
			ser.close()
			while(cv2.waitKey(1) & 0xFF != ord('w')):
				continue
			ser.open()
