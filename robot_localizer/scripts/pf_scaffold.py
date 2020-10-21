#!/usr/bin/env python3

""" This is the starter code for the robot localization project """

import rospy
import placeParticles as pp

from std_msgs.msg import Header, String
from sensor_msgs.msg import LaserScan, PointCloud
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, PoseArray, Pose, Point, Quaternion
from nav_msgs.srv import GetMap
from copy import deepcopy

import tf
from tf import TransformListener
from tf import TransformBroadcaster
from tf.transformations import euler_from_quaternion, rotation_matrix, quaternion_from_matrix, quaternion_from_euler
from random import gauss

import math
import time

import numpy as np
from numpy.random import random_sample
from sklearn.neighbors import NearestNeighbors
from occupancy_field import OccupancyField
from helper_functions import TFHelper

from occupancy_field import OccupancyField
import helper

from visualization_msgs.msg import Marker
from visualization_msgs.msg import MarkerArray

class Particle(object):
    """ Represents a hypothesis (particle) of the robot's pose consisting of x,y and theta (yaw)
        Attributes:
            x: the x-coordinate of the hypothesis relative to the map frame
            y: the y-coordinate of the hypothesis relative ot the map frame
            theta: the yaw of the hypothesis relative to the map frame
            w: the particle weight (the class does not ensure that particle weights are normalized
    """

    def __init__(self,x=0.0,y=0.0,theta=0.0,w=1.0):
        """ Construct a new Particle
            x: the x-coordinate of the hypothesis relative to the map frame
            y: the y-coordinate of the hypothesis relative ot the map frame
            theta: the yaw of the hypothesis relative to the map frame
            w: the particle weight (the class does not ensure that particle weights are normalized """ 
        self.w = w
        self.theta = theta
        self.x = x
        self.y = y

    def as_pose(self):
        """ A helper function to convert a particle to a geometry_msgs/Pose message """
        orientation_tuple = tf.transformations.quaternion_from_euler(0,0,self.theta)
        return Pose(position=Point(x=self.x,y=self.y,z=0), orientation=Quaternion(x=orientation_tuple[0], y=orientation_tuple[1], z=orientation_tuple[2], w=orientation_tuple[3]))

    # TODO: define additional helper functions if needed




class ParticleFilter:
    """ The class that represents a Particle Filter ROS Node
        Attributes list:
            initialized: a Boolean flag to communicate to other class methods that initializaiton is complete
            base_frame: the name of the robot base coordinate frame (should be "base_link" for most robots)
            map_frame: the name of the map coordinate frame (should be "map" in most cases)
            odom_frame: the name of the odometry coordinate frame (should be "odom" in most cases)
            scan_topic: the name of the scan topic to listen to (should be "scan" in most cases)
            n_particles: the number of particles in the filter
            d_thresh: the amount of linear movement before triggering a filter update
            a_thresh: the amount of angular movement before triggering a filter update
            laser_max_distance: the maximum distance to an obstacle we should use in a likelihood calculation
            pose_listener: a subscriber that listens for new approximate pose estimates (i.e. generated through the rviz GUI)
            particle_pub: a publisher for the particle cloud
            laser_subscriber: listens for new scan data on topic self.scan_topic
            tf_listener: listener for coordinate transforms
            tf_broadcaster: broadcaster for coordinate transforms
            particle_cloud: a list of particles representing a probability distribution over robot poses
            current_odom_xy_theta: the pose of the robot in the odometry frame when the last filter update was performed.
                                   The pose is expressed as a list [x,y,theta] (where theta is the yaw)
            map: the map we will be localizing ourselves in.  The map should be of type nav_msgs/OccupancyGrid
    """
    def __init__(self):
        self.initialized = False        # make sure we don't perform updates before everything is setup
        rospy.init_node('mypf')           # tell roscore that we are creating a new node named "pf"

        self.base_frame = "base_link"   # the frame of the robot base
        self.map_frame = "map"          # the name of the map coordinate frame
        self.odom_frame = "odom"        # the name of the odometry coordinate frame
        self.scan_topic = "scan"        # the topic where we will get laser scans from 

         # enable listening for and broadcasting coordinate transforms
        self.tf_listener = TransformListener()
        self.tf_broadcaster = TransformBroadcaster()

        self.occupancy_field = OccupancyField()


        self.n_particles = 300      # the number of particles to use

        self.d_thresh = 0.002            # the amount of linear movement before performing an update
        self.a_thresh = np.pi/6       # the amount of angular movement before performing an update

        self.laser_max_distance = 2.0   # maximum penalty to assess in the likelihood field model

        # TODO: define additional constants if needed
    
        # Setup pubs and subs

        # pose_listener responds to selection of a new approximate robot location (for instance using rviz)
        rospy.Subscriber("initialpose", PoseWithCovarianceStamped, self.update_initial_pose)

        # publish the current particle cloud.  This enables viewing particles in rviz.
        self.particle_pub = rospy.Publisher("my_particle_cloud", PoseArray, queue_size=10)

        # publish visualization markers
        self.markerArrayPub = rospy.Publisher("markers", MarkerArray)

        # laser_subscriber listens for data from the lidar
        rospy.Subscriber(self.scan_topic, LaserScan, self.scan_received)
        
        self.particle_cloud = []

        # change use_projected_stable_scan to True to use point clouds instead of laser scans
        self.use_projected_stable_scan = True
        self.last_projected_stable_scan = None
        if self.use_projected_stable_scan:
            # subscriber to the odom point cloud
            rospy.Subscriber("projected_stable_scan", PointCloud, self.projected_scan_received)

        self.current_odom_xy_theta = []
        self.occupancy_field = OccupancyField()
        self.transform_helper = TFHelper()
        self.avgPose = np.array([0,0,0]).astype(float)
        self.initialized = True
        print("Init")


    def update_robot_pose(self, timestamp):
        """ Update the estimate of the robot's pose given the updated particles.
            There are two logical methods for this:
                (1): compute the mean pose
                (2): compute the most likely pose (i.e. the mode of the distribution)
        """
        # first make sure that the particle weights are normalized
        # self.normalize_particles()
        avgQuatern = quaternion_from_euler(0, 0, self.avgPose[2])
        

        self.robot_pose = Pose(position=Point(x=self.avgPose[0],
                                   y=self.avgPose[1],
                                   z=0),
                    orientation= Quaternion(x=avgQuatern[0], y=avgQuatern[1], z=avgQuatern[2], w=avgQuatern[3]))

        # print(self.robot_pose)

        # TODO: assign the latest pose into self.robot_pose as a geometry_msgs.Pose object
        # just to get started we will fix the robot's pose to always be at the origin
        # self.robot_pose = Pose()

        self.transform_helper.fix_map_to_odom_transform(self.robot_pose, timestamp)

    def projected_scan_received(self, msg):
        self.last_projected_stable_scan = msg

    def update_particles_with_odom(self, msg):
        """ Update the particles using the newly given odometry pose.
            The function computes the value delta which is a tuple (x,y,theta)
            that indicates the change in position and angle between the odometry
            when the particles were last updated and the current odometry.

            msg: this is not really needed to implement this, but is here just in case.
        """
        # print("update_particles_with_odom")
        # p = PoseStamped(header=Header(stamp=msg.header.stamp, frame_id=self.odom_frame) ,pose=self.odom_pose.pose)
        # self.tf_listener.waitForTransform()
        # self.map_pose = self.tf_listener.transformPose(self.map_frame, p)
        
        new_odom_xy_theta = self.transform_helper.convert_pose_to_xy_and_theta(self.odom_pose.pose)
        # compute the change in x,y,theta since our last update
        delta = (0,0,0)
        if self.current_odom_xy_theta:
            old_odom_xy_theta = self.current_odom_xy_theta
            delta = (new_odom_xy_theta[0] - self.current_odom_xy_theta[0],
                     new_odom_xy_theta[1] - self.current_odom_xy_theta[1],
                     new_odom_xy_theta[2] - self.current_odom_xy_theta[2])

            self.current_odom_xy_theta = new_odom_xy_theta
        else:
            self.current_odom_xy_theta = new_odom_xy_theta
        
        return delta

        # TODO: modify particles using delta

    def map_calc_range(self,x,y,theta):
        """ Difficulty Level 3: implement a ray tracing likelihood model... Let me know if you are interested """
        # TODO: nothing unless you want to try this alternate likelihood model
        pass


    def resample_particles(self):
        """ Resample the particles according to the new particle weights.
            The weights stored with each particle should define the probability that a particular
            particle is selected in the resampling step.  You may want to make use of the given helper
            function draw_random_sample.
        """
        try:
            particles = np.random.choice(a=self.particle_cloud, size=(self.n_particles, 1, 1), p=self.weightsNorm)
            reshapedParticle = np.array(particles).reshape((len(particles)))
            copiedParticles = []
            for i in reshapedParticle:
                copiedParticles.append(deepcopy(i))
        
            # print(len(reshapedParticle))
            self.particle_cloud = copiedParticles
            # self.publish_particles("publishing")
        except ValueError:
            pass
            
        # print(particles)
        # make sure the distribution is normalized
        #self.normalize_particles()
        # TODO: fill out the rest of the implementation

    def update_particles_with_laser(self, msg):
        """ Updates the particle weights in response to the scan contained in the msg """
        # TODO: implement this
        pass

    @staticmethod
    def draw_random_sample(choices, probabilities, n):
        """ Return a random sample of n elements from the set choices with the specified probabilities
            choices: the values to sample from represented as a list
            probabilities: the probability of selecting each element in choices represented as a list
            n: the number of samples
        """
        values = np.array(range(len(choices)))
        probs = np.array(probabilities)
        bins = np.add.accumulate(probs)
        inds = values[np.digitize(random_sample(n), bins)]
        samples = []
        for i in inds:
            samples.append(deepcopy(choices[int(i)]))
        return samples

    def update_initial_pose(self, msg):
        """ Callback function to handle re-initializing the particle filter based on a pose estimate.
            These pose estimates could be generated by another ROS Node or could come from the rviz GUI """
        # print("Updating")

        xy_theta = self.transform_helper.convert_pose_to_xy_and_theta(msg.pose.pose) # convert the pose of the inital guess arrow to xy_theta
        myCloud = pp.placeParticles() # create placeParticles object
        self.particle_cloud = myCloud.createRandomXYs(*xy_theta, self.n_particles) # create the n particles centered around xy_theta
        self.publish_particles("publishing")



    def initialize_particle_cloud(self, timestamp, xy_theta=None):
        """ Initialize the particle cloud.
            Arguments
            xy_theta: a triple consisting of the mean x, y, and theta (yaw) to initialize the
                      particle cloud around.  If this input is omitted, the odometry will be used """
        if xy_theta is None:
            xy_theta = self.transform_helper.convert_pose_to_xy_and_theta(self.odom_pose.pose)
        self.particle_cloud = []
        # TODO create particles

        self.normalize_particles()
        self.update_robot_pose(timestamp)

    def normalize_particles(self):
        """ Make sure the particle weights define a valid distribution (i.e. sum to 1.0) """
        # TODO: implement this
        pass

    def publish_particles(self, msg):
        # print("Published")
        particles_conv = []
        for p in self.particle_cloud:
            particles_conv.append(p.as_pose())
        # actually send the message so that we can view it in rviz
        
        self.particle_pub.publish(PoseArray(header=Header(stamp=rospy.Time.now(),
                                            frame_id=self.map_frame),
                                  poses=particles_conv))

    def transform_scan(self, point, shift):
        """ Takes in an [x,y] point and transforms it by [dx, dy, da] shift
        http://planning.cs.uiuc.edu/node99.html
        
        """
        x = point[0]
        y = point[1]

        x_prime = x*np.cos(shift[2]) - y*np.sin(shift[2]) + shift[0]
        y_prime = x*np.sin(shift[2]) + y*np.cos(shift[2]) + shift[1]

        return x_prime, y_prime

    def visualize_particle_scan(self, markerArray):
        """ Will create marker array
        """
        self.markerArrayPub.publish(markerArray)

    def scan_received(self, msg):
        """ This is the default logic for what to do when processing scan data.
            Feel free to modify this, however, we hope it will provide a good
            guide.  The input msg is an object of type sensor_msgs/LaserScan """

        
        if not(self.initialized):
            # wait for initialization to complete
            return

        self.tf_listener.waitForTransform(self.base_frame, self.odom_frame, msg.header.stamp, rospy.Duration(2))

        if not(self.tf_listener.canTransform(self.base_frame, msg.header.frame_id, msg.header.stamp)):
            # need to know how to transform the laser to the base frame
            # this will be given by either Gazebo or neato_node
            print("If 2")
            return

        # print("list of frames: ", self.tf_listener.getFrameStrings())
        if not(self.tf_listener.canTransform(self.base_frame, self.odom_frame, msg.header.stamp)):
            # print("odom: ", self.tf_listener.frameExists(self.odom_frame), "base: ", self.tf_listener.frameExists(self.base_frame))
            # 
            # need to know how to transform between base and odometric frames
            # this will eventually be published by either Gazebo or neato_node
            print("if 3")
            return

        # calculate pose of laser relative to the robot base
        p = PoseStamped(header=Header(stamp=rospy.Time(0),
                                      frame_id=msg.header.frame_id))

        self.laser_pose = self.tf_listener.transformPose(self.base_frame, p)

        # find out where the robot thinks it is based on its odometry
        p = PoseStamped(header=Header(stamp=msg.header.stamp, frame_id=self.base_frame) ,pose=Pose())
        
        self.odom_pose = self.tf_listener.transformPose(self.odom_frame, p)
        # store the the odometry pose in a more convenient format (x,y,theta)
        new_odom_xy_theta = self.transform_helper.convert_pose_to_xy_and_theta(self.odom_pose.pose)

        delta = self.update_particles_with_odom(msg)
        dx = delta[0] #+ np.random.normal(delta[0], scale=1)
        dy = delta[1] #+  np.random.normal(delta[1], scale=1)
        da = delta[2] #+  np.random.normal(delta[2], scale=0.8)  # update based on odometry, returns the delta to move the particles
        # print(delta)
        dist = (dx**2 + dy**2)**0.5
        

        if math.fabs(dx) >= self.d_thresh or math.fabs(dy) >= self.d_thresh or math.fabs(da) >= self.a_thresh:
            for i in range(len(self.particle_cloud)):
                self.particle_cloud[i].x += dist*np.cos(self.particle_cloud[i].theta) + np.random.normal(0, 0.05)
                self.particle_cloud[i].y += dist*np.sin(self.particle_cloud[i].theta) + np.random.normal(0, 0.05)
                self.particle_cloud[i].theta += da + np.random.normal(0, 0.05)
        
        if not self.current_odom_xy_theta:
            self.current_odom_xy_theta = new_odom_xy_theta
            # print("currentodom")
            return
            

        if not(list(self.particle_cloud)):
            # now that we have all of the necessary transforms we can update the particle cloud
            # print("no cloud")
            self.initialize_particle_cloud(msg.header.stamp)

        
        # weight each particle
        # use the normal scan
        # lidar_scan = np.array(msg.ranges)
        self.update_robot_pose(msg.header.stamp) 

        if self.last_projected_stable_scan:
            last_projected_scan_timeshift = deepcopy(self.last_projected_stable_scan)
            last_projected_scan_timeshift.header.stamp = msg.header.stamp
            self.scan_in_base_link = self.tf_listener.transformPointCloud("base_link", last_projected_scan_timeshift)
            scan = self.scan_in_base_link.points # geometry_msgs.msg._Point.Point
            
        myMarkerArray = MarkerArray()    
        weights = []
        avgPose = np.array([0,0,0]).astype(float)
        for i in range(len(self.particle_cloud)):
            # particles are in odom frame. Current scan is in base_link frame. 
            # Need to transform scan to odom frame, then transform them to each particle
            particle_pose = (self.particle_cloud[i].x, self.particle_cloud[i].y, self.particle_cloud[i].theta)
            # avgPose += np.array([particle_pose]).reshape((3))
            # for each point in the scan, visualize each one and calculate point's distance to the map
            distances = 0
            for j in range(0, len(scan), 10):
                
                transformedScan = self.transform_scan([scan[j].x, scan[j].y], particle_pose)
                # calculate weight for each particle
                distances += self.occupancy_field.get_closest_obstacle_distance(transformedScan[0], transformedScan[1])
                marker = helper.create_marker(self.map_frame, f"translated_scan_{i},{j}", transformedScan[0], transformedScan[1])
                myMarkerArray.markers.append(marker)
            weights.append(distances/len(scan))
            # self.visualize_particle_scan(myMarkerArray)
        
        
        # for i in range(len(self.particle_cloud)):
            


        # self.visualize_particle_scan([helper.create_marker(self.map_frame, "average", avgPose[0], avgPose[1])])
        weights = np.nan_to_num(weights, nan = 0) 
        #print(self.particle_cloud)
        sumWeights = np.sum(weights)
        self.weightsNorm = np.array(weights)/sumWeights
        # self.avgPose = np.average(self.particle_cloud, weights=self.weightsNorm)
        
        for i in range(len(self.particle_cloud)):
            particle_pose = (self.particle_cloud[i].x, self.particle_cloud[i].y, self.particle_cloud[i].theta)
            avgPose += self.weightsNorm[i]*np.array([particle_pose]).reshape((3))
            
        self.avgPose = avgPose

        # print("Resampling")
        self.resample_particles()
        self.publish_particles(msg)
        
        # self.resample_particles()
        
            # visualizes the marker array (lidar points for all particles)
            
           

        # self.update_particles_with_laser(msg)   # update based on laser scan
        # self.update_robot_pose(msg.header.stamp)                # update robot's pose
        # self.resample_particles()    

        # if (math.fabs(new_odom_xy_theta[0] - self.current_odom_xy_theta[0]) > self.d_thresh or
        #       math.fabs(new_odom_xy_theta[1] - self.current_odom_xy_theta[1]) > self.d_thresh or
        #       math.fabs(new_odom_xy_theta[2] - self.current_odom_xy_theta[2]) > self.a_thresh):

        #     print("elif passed")
            
            # if self.last_projected_stable_scan:
            #     last_projected_scan_timeshift = deepcopy(self.last_projected_stable_scan)
            #     last_projected_scan_timeshift.header.stamp = msg.header.stamp
            #     self.scan_in_base_link = self.tf_listener.transformPointCloud("base_link", last_projected_scan_timeshift)

            # self.update_particles_with_laser(msg)   # update based on laser scan
            # self.update_robot_pose(msg.header.stamp)                # update robot's pose
            # self.resample_particles()               # resample particles to focus on areas of high density
        # publish particles (so things like rviz can see them)
        


if __name__ == '__main__':
    myFilter = ParticleFilter()
    r = rospy.Rate(5)
    

    while not(rospy.is_shutdown()):
        # in the main loop all we do is continuously broadcast the latest map to odom transform
        myFilter.transform_helper.send_last_map_to_odom_transform()
        r.sleep()
