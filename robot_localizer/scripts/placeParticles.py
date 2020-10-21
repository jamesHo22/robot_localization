#!/usr/bin/env python3

import pf_scaffold as pf
import rospy

from std_msgs.msg import Header, String
from sensor_msgs.msg import LaserScan, PointCloud
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, PoseArray, Pose, Point, Quaternion
from nav_msgs.srv import GetMap
from copy import deepcopy

import tf
from tf import TransformListener
from tf import TransformBroadcaster
from tf.transformations import euler_from_quaternion, rotation_matrix, quaternion_from_matrix
from random import gauss

import math
import time

import numpy as np
from numpy.random import random_sample
from sklearn.neighbors import NearestNeighbors
from occupancy_field import OccupancyField
from helper_functions import TFHelper
from visualization_msgs.msg import Marker


class placeParticles():
    """
    This node creates random particles and visualizes them in rviz
    """
    

    def __init__(self):
        #markerPub = rospy.Publisher('robotMarker', Marker, queue_size=10)
        # list of all particles
        self.particles = []
        # number of particles
        self.xCenter = 0
        self.yCenter = 0
        self.orientationCenter = 0
        

    def createRandomXYs(self, x, y, theta, n_particles):
        """
        Create a list of poses with xy's centered around a point
        """
        self.xCenter = x
        self.yCenter = y
        self.orientationCenter = theta
        self.n = n_particles
        self.xCoords = np.random.normal(self.xCenter, size = self.n, scale=0.1)
        self.yCoords = np.random.normal(self.yCenter, size = self.n, scale=0.1)
        
        for i in range(self.n):
            particle = pf.Particle(x=self.xCoords[i], y=self.yCoords[i],theta = np.random.normal(theta, scale=0.05))
            self.particles.append(particle)
        # for i in range(self.n):
        #     particle = pf.Particle(x=x, y=y,theta = theta)
        #     self.particles.append(particle)
        # print(self.particles)
        return self.particles


    def visualizePoints(self):
        '''
        marker = Marker()
        marker.header.frame_id = "map"
        marker.color=ColorRGB(0, 0, 1)
        marker.scale = [0.5,0.5,0.5]
        for i in range(self.n):
            marker.pose.position.x = self.xCoords[i]
            marker.pose.position.y = self.yCoords[i]
        '''
            
            

        


if __name__ == '__main__':
    myFilter = pf.ParticleFilter()
    myCloud = placeParticles()
    myCloud.createRandomXYs()
    myFilter.particle_cloud = myCloud.particles
    myFilter.publish_particles("publish")
    print(myFilter.particle_cloud[0].x)
    r = rospy.Rate(50)

    while not(rospy.is_shutdown()):
        # in the main loop all we do is continuously broadcast the latest map to odom transform
        myFilter.transform_helper.send_last_map_to_odom_transform()
        r.sleep()
