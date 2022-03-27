#!/usr/bin/env python

import rospy
import numpy as np
import time

from scipy.spatial.transform import Rotation as R
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float64

from planner.msg import State
from controller.controller_utils import wrap_angle

class Mocap():
    """Process and publish motion capture measurements

    """
    def __init__(self):
        # Parameters (eventually make these global)

        # Initialize node 
        rospy.init_node('Mocap', anonymous=True)
        self.rate = rospy.Rate(100)

        # Class variables
        self.x = 0
        self.y = 0
        self.theta = 0
        self.v = 0
        self.t_prev = 0
        self.v_hist = np.zeros((1,20))

        # Publishers and subscribers
        mocap_sub = rospy.Subscriber('vrpn_client_node/rover/pose', PoseStamped, self.mocap_callback)
        self.mocap_pub = rospy.Publisher('sensing/mocap', State, queue_size=1)
        self.debug_pub = rospy.Publisher('debug/mocap_v', Float64, queue_size=1)


    def mocap_callback(self, data):
        """Mocap subscriber callback

        Receive and save mocap data as measurement.

        """
        pos = data.pose.position
        q = data.pose.orientation

        quat = np.array([q.x, q.y, q.z, q.w])
        r = R.from_quat(quat)
        self.theta = wrap_angle(r.as_euler('zyx')[0])

        dt = time.time() - self.t_prev
        v = np.sqrt((self.x - pos.x)**2 + (self.y - pos.y)**2) / dt
        if v - self.v < 0.1:  # filter the velocity measurement
            self.v = v
        self.t_prev = time.time()

        self.debug_pub.publish(self.v)

        self.x = pos.x; self.y = pos.y

        rospy.loginfo("Received data: (%f, %f, %f, %f)", self.x, self.y, self.theta, self.v)


    def publish(self):
        """Publish latest measurement

        """
        s = State()
        s.x = self.x
        s.y = self.y
        s.theta = self.theta
        s.v = self.v
        self.mocap_pub.publish(s)


    def run(self):
        rospy.loginfo("Running Mocap node")
        while not rospy.is_shutdown():
            
            self.publish()

            self.rate.sleep()
        
        # spin() simply keeps python from exiting until this node is stopped
        rospy.spin()


if __name__ == '__main__':
    mocap = Mocap()
    try:
        mocap.run()
    except rospy.ROSInterruptException:
        pass