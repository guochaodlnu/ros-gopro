#!/usr/bin/env python
import numpy as np
import cv2
import rospy
import math
import rospkg
from sensor_msgs.msg import Image
from std_msgs.msg import Int64
from gopro.msg import Status
from cv_bridge import CvBridge, CvBridgeError
from rect.rect import Rect

class Analyzer:
    
	def callbackGoProPicture(self, data):
		try:
		    cv_image = self.bridge.imgmsg_to_cv2(data)
		    self.analyze(cv_image)
		except CvBridgeError as e:
			rospy.logerr("PB Bridge : ")
			rospy.logerr(e)
		
    
	def callbackGoProStatus(self, data):
	    cameraSX = data.sx
	    if cameraSX :
	        if cameraSX.vidres in self.videoResolutions:
				self.vidRes = self.videoResolutions[cameraSX.vidres]
	        self.fov = float(cameraSX.fov)
	
	def __init__(self):
		rospack = rospkg.RosPack()
		path = rospack.get_path('analyzer')
		self.face_cascade = cv2.CascadeClassifier(path + '/resources/haarcascade_frontalface_default.xml')
		self.eye_cascade = cv2.CascadeClassifier(path + '/resources/haarcascade_eye.xml')
		self.bridge = CvBridge()
		
		#self.cameraHorizontalAngles = {'wide' : 170, 'normal' : 127, 'narrow' : 90}
		self.videoResolutions = {'720p SuperView' : (9.0/16.0), '920p' : (3.0/4.0)}
		
		self.vidRes = self.videoResolutions['720p SuperView']
		self.fov = 170.0
        
        rospy.init_node('analyzer', anonymous=True)
        
	def initSubscribe(self):
	    rospy.Subscriber('/gopro/camera/picture', Image, self.callbackGoProPicture)
	    rospy.Subscriber('/gopro/status', Status, self.callbackGoProStatus)
        
	def initPublish(self):
	    self.takePicturePub = rospy.Publisher('/gopro/camera/take_picture', Int64, queue_size=10)
	
	def start(self):
		rate = rospy.Rate(1) # 10hz
		while not rospy.is_shutdown():
			self.takePicturePub.publish(1)
	
	def analyze(self, img):
		rospy.logerr("Analyzing...")
		# Determine vertical video angle
		
		verticalAngle = self.fov * self.vidRes
		
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
		(height, width, _) = img.shape
		cv2.circle(img, (int(width/2), int(height/2)), 3, (0, 0, 255), -1)
		faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
		
		for (x,y,w,h) in faces:
			rectangle = Rect((x,y,w,h))
			(xCent, yCent) = rectangle.get_center()
			
			roi_gray = gray[y:y+h, x:x+w]
			roi_color = img[y:y+h, x:x+w]
			eyes = self.eye_cascade.detectMultiScale(roi_gray)
			
			if len(eyes) >= 2 :
				cv2.putText(img,"Face detected", (0,150), cv2.FONT_HERSHEY_SIMPLEX, 5, (0,0,255), 5)
				cv2.circle(img, (int(xCent), int(yCent)), 3, (0, 255, 0), -1)
				cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
				
				#Compute distance between screen center and face center in degree
				horizontalDistanceAngle = 0
				verticalDistanceAngle = 0
				if xCent < (width/2.0):
					distance = math.fabs(xCent - (width/2.0))
					horizontalDistanceAngle = self.fov * distance / width
					rospy.logerr("Left : " + str(horizontalDistanceAngle) + " degrees")
				elif xCent > (width/2.0):
					distance = math.fabs(xCent - (width/2.0))
					horizontalDistanceAngle = self.fov * distance / width
					rospy.logerr("Right : " + str(horizontalDistanceAngle) + " degrees")
				if yCent < (height/2.0):
					distance = math.fabs(yCent - (height/2.0))
					verticalDistanceAngle = verticalAngle * distance / height
					rospy.logerr("Top : " + str(verticalDistanceAngle) + " degrees")
				elif yCent > (height/2.0):
					distance = math.fabs(yCent - (height/2.0))
					verticalDistanceAngle = verticalAngle * distance / height
					rospy.logerr("Bottom : " + str(verticalDistanceAngle) + " degrees")

		cv2.imwrite('img.jpg', img)

if __name__ == '__main__':
    anal = Analyzer()
    anal.initSubscribe()
    anal.initPublish()
    #anal.test('4:3')
    anal.start()
