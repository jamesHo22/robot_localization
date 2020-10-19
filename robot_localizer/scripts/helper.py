""" This code holds a bunch of helper functions that is used in
    the neato nodes. 
"""

import math, rospy
from visualization_msgs.msg import Marker
from tf.transformations import euler_from_quaternion

def create_marker(frame, ns, posx, posy, posz=0, mtype=Marker.SPHERE, \
                  scalex=.2, scaley=.2, scalez=.2, r=0, g=1, b=0, a=1, maction=3):
    """ Creates a visualization marker to display in rviz """
    marker = Marker()
    marker.header.frame_id = frame
    marker.header.stamp = rospy.Time.now()
    marker.ns = ns
    marker.id = 0
    marker.type = mtype
    marker.action = Marker.ADD 
    marker.pose.position.x = posx
    marker.pose.position.y = posy
    marker.pose.position.z = posz
    marker.pose.orientation.x = 0.0
    marker.pose.orientation.y = 0.0
    marker.pose.orientation.z = 0.0
    marker.pose.orientation.w = 1.0
    marker.scale.x = scalex
    marker.scale.y = scaley
    marker.scale.z = scalez
    marker.color.a = a
    marker.color.r = r
    marker.color.g = g
    marker.color.b = b
    return marker

def convert_pose_to_xy_and_theta(pose):
    """ Convert pose (geometry_msgs.Pose) to a (x,y,yaw) tuple """
    orientation_tuple = (pose.orientation.x,
                            pose.orientation.y,
                            pose.orientation.z,
                            pose.orientation.w)
    angles = euler_from_quaternion(orientation_tuple)
    return (pose.position.x, pose.position.y, angles[2])

def neato_to_odom(a, b, c, d, theta):
    """ Converts a point in the neato frame to odom frame 
    
    Args:
        a: x in neato
        b: y in neato
        c: x of neato in world
        d: y of neato in world
        theta: the rotation neato is to the world
    """
    r_x = math.cos(theta) * a - math.sin(theta) * b + c
    r_y = math.sin(theta) * a + math.cos(theta) * b + d
    return r_x, r_y

# Helper Functions for angle calcs
def angle_normalize(z):
    """ convenience function to map an angle to the range [-pi,pi] """
    return math.atan2(math.sin(z), math.cos(z))

def angle_diff(a, b):
    """ Calculates the difference between angle a and angle b (both should be in radians)
            the difference is always based on the closest rotation from angle a to angle b
        examples:
            angle_diff(.1,.2) -> -.1
            angle_diff(.1, 2*math.pi - .1) -> .2
            angle_diff(.1, .2+2*math.pi) -> -.1
    """
    a = angle_normalize(a)
    b = angle_normalize(b)

    d1 = a-b
    d2 = 2*math.pi - math.fabs(d1)
    if d1 > 0:
        d2 *= -1.0
    if math.fabs(d1) < math.fabs(d2):
        return d1
    else:
        return d2   

def sigmoid(x):
    return 1/(1+math.exp(-x))