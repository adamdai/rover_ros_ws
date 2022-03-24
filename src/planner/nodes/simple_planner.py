#!/usr/bin/env python

# Publishes a set nominal trajectory to be tracked

import rospy
import numpy as np
import sys

from planner.msg import State, Control, NominalTrajectory
from planner.planner_utils import *


class simple_planner():
    """Simple Planner

    Node which publishes a nominal trajectory parameterized by desired linear and angular speed.

    """
    def __init__(self, kw, kv):
        # parameters (eventually make global)
        self.max_acc_mag = 0.25
        self.t_plan = 3.0
        self.dt = 0.2

        # initialize node 
        rospy.init_node('simple_planner', anonymous=True)
        self.rate = rospy.Rate(10)

        # publishers
        self.traj_pub = rospy.Publisher('planner/traj', NominalTrajectory, queue_size=10)

        # subscribers
        state_est_sub = rospy.Subscriber('controller/state_est', State, self.state_est_callback)

        # class variables
        self.x_hat = np.zeros((4,1))
        self.traj_msg = None
        self.kw = kw
        self.kv = kv

    
    def state_est_callback(self, data):
        """State estimator subscriber callback

        Save received state estimate.

        """
        self.x_hat = np.array([[data.x],[data.y],[data.theta],[data.v]])


    def generate_trajectory(self):
        """Generate trajectory msg from parameters
        """
        rospy.loginfo("Generating nominal trajectory with w = %f, v = %f", kw, kv)

        x_nom, u_nom = trajectory_parameter_to_nominal_trajectory(
            self.kw, self.kv, self.x_hat, self.t_plan, self.dt, self.max_acc_mag)

        rospy.loginfo("Final state: x = %f, y = %f, theta = %f", x_nom[0][-1], x_nom[1][-1], x_nom[2][-1])

        self.traj_msg = NominalTrajectory()
        self.traj_msg.states = wrap_states(x_nom)
        self.traj_msg.controls = wrap_controls(u_nom)
        

    def publish_trajectory(self):
        self.traj_pub.publish(self.traj_msg)


    def run(self):
        rospy.loginfo("Running Simple Planner")

        while not rospy.is_shutdown():
            connections = self.traj_pub.get_num_connections()
            rospy.loginfo("Connections: %d", connections)

            if connections > 0:
                self.generate_trajectory()
                self.publish_trajectory()
                rospy.loginfo("Published trajectory")
                break
            self.rate.sleep()
            
        # spin() simply keeps python from exiting until this node is stopped
        rospy.spin()


if __name__ == '__main__':
    if len(sys.argv) < 3:
        # default kw and kv
        kw = 0.0
        kv = 0.5
    else:
        kw = float(sys.argv[1])
        kv = float(sys.argv[2])

    sp = simple_planner(kw, kv)
    try:
        sp.run()
    except rospy.ROSInterruptException:
        pass
