#! /usr/bin/env python

## @package rt2_assignment1
# \file go_to_point.py
# \brief This node drives the robot toward the random position and orientation in the environment
# \author Serena Paneri 4506977
# \version 1.0
# \date 16/08/2022
#
# \details
#
# Subscribes to: <BR>
#	/odom
#
# Publishes to: <BR>
#	/cmd_vel
#
# Action server: <BR>
# 	/go_to_point
#
# Description:
# This node implements an action server and its objective is to make the robot reach the given
# target position and orientation in the environment. The use of an action server is adopted since
# it provides more functionalities, including the possibility of recieving feedbacks and, moreover, the
# possibility to cancel a goal and make the robot stops immediately and not only after it has achieved 
# the target position. 
#



import rospy
import rt2_assignment1.msg
import actionlib
import actionlib.msg
from geometry_msgs.msg import Twist, Point
from nav_msgs.msg import Odometry
from tf import transformations
from rt2_assignment1.srv import Position
import math

# robot state variables
position_ = Point()
yaw_ = 0
position_ = 0
state_ = 0

# publisher used for cmd_vel
pub_ = None

# action server
act_s = None

# parameters for control
yaw_precision_ = math.pi / 9  # +/- 20 degree allowed
yaw_precision_2_ = math.pi / 90  # +/- 2 degree allowed
dist_precision_ = 0.1
kp_a = -3.0 
kp_d = 0.2
ub_a = 0.6
lb_a = -0.5
ub_d = 0.6

##
# \param msg: information about the position and orientation of the robot
#
# This is the callback function that is used to know the actual position and orientation of
# the robot in the space exploiting the topic /odom.
#

def clbk_odom(msg):

    global position_
    global yaw_

    # position
    position_ = msg.pose.pose.position

    # yaw
    quaternion = (
        msg.pose.pose.orientation.x,
        msg.pose.pose.orientation.y,
        msg.pose.pose.orientation.z,
        msg.pose.pose.orientation.w)
    euler = transformations.euler_from_quaternion(quaternion)
    yaw_ = euler[2]


##
# \param state: contains the state of the robot
#
# With this function we are able to switch between the different states in which the robot
# could be.
#

def change_state(state):

    global state_
    state_ = state
    print ('State changed to [%s]' % state_)


##
# \param angle: contains the angle of the robot
#
# \retval angle: returns the normalized angle
#
# This function is used to normalized the angle.
#


def normalize_angle(angle):

    if(math.fabs(angle) > math.pi):
        angle = angle - (2 * math.pi * angle) / (math.fabs(angle))
    return angle

    
##
# \param des_pos: desired position to be achieved by the robot
#
# This function is used to adjust the yaw angle of the robot in a way that 
# it is directly alligned with the target position to be reached.
#    

def fix_yaw(des_pos):

    desired_yaw = math.atan2(des_pos.y - position_.y, des_pos.x - position_.x)
    err_yaw = normalize_angle(desired_yaw - yaw_)
    rospy.loginfo(err_yaw)
    twist_msg = Twist()
    if math.fabs(err_yaw) > yaw_precision_2_:
        twist_msg.angular.z = kp_a*err_yaw
        if twist_msg.angular.z > ub_a:
            twist_msg.angular.z = ub_a
        elif twist_msg.angular.z < lb_a:
            twist_msg.angular.z = lb_a
    pub_.publish(twist_msg)
    # state change conditions
    if math.fabs(err_yaw) <= yaw_precision_2_:
        #print ('Yaw error: [%s]' % err_yaw)
        change_state(1)


##
# \param des_pos: desired position to be achieved by the robot
#
# This function allows the robot to move straight to reach the goal position.
#  

def go_straight_ahead(des_pos):

    desired_yaw = math.atan2(des_pos.y - position_.y, des_pos.x - position_.x)
    err_yaw = desired_yaw - yaw_
    err_pos = math.sqrt(pow(des_pos.y - position_.y, 2) +
                        pow(des_pos.x - position_.x, 2))
    err_yaw = normalize_angle(desired_yaw - yaw_)
    rospy.loginfo(err_yaw)

    if err_pos > dist_precision_:
        twist_msg = Twist()
        twist_msg.linear.x = 0.3
        if twist_msg.linear.x > ub_d:
            twist_msg.linear.x = ub_d

        twist_msg.angular.z = kp_a*err_yaw
        pub_.publish(twist_msg)
    else: # state change conditions
        #print ('Position error: [%s]' % err_pos)
        change_state(2)

    # state change conditions
    if math.fabs(err_yaw) > yaw_precision_:
        #print ('Yaw error: [%s]' % err_yaw)
        change_state(0)


##
# \param des_yaw: desired yaw angle to be achieved by the robot
#
# This function allows the robot to adjust its goal orientation.
#

def fix_final_yaw(des_yaw):

    err_yaw = normalize_angle(des_yaw - yaw_)
    rospy.loginfo(err_yaw)
    twist_msg = Twist()
    if math.fabs(err_yaw) > yaw_precision_2_:
        twist_msg.angular.z = kp_a*err_yaw
        if twist_msg.angular.z > ub_a:
            twist_msg.angular.z = ub_a
        elif twist_msg.angular.z < lb_a:
            twist_msg.angular.z = lb_a
    pub_.publish(twist_msg)
    # state change conditions
    if math.fabs(err_yaw) <= yaw_precision_2_:
        #print ('Yaw error: [%s]' % err_yaw)
        change_state(3)


##
#
# This function is used to stop the robot.
#
        
def done():

    twist_msg = Twist()
    twist_msg.linear.x = 0
    twist_msg.angular.z = 0
    pub_.publish(twist_msg)
 
    
##
# \param goal: desired goal in the environment to be achieved
#
# This function is used to regulate the different states of the robot in a way 
# to achieve the correct behavior to be followed in order to reach the goal.
#


def go_to_point(goal):

    desired_position = Point()
    desired_position.x = goal.x
    desired_position.y = goal.y
    des_yaw = goal.theta
    
    rate = rospy.Rate(20)
    success = True
    
    change_state(0)
    
    feedback = rt2_assignment1.msg.TargetFeedback()
    result = rt2_assignment1.msg.TargetResult()
    
    while not rospy.is_shutdown():
        if act_s.is_preempt_requested():
            rospy.loginfo('Goal was preempted')
            act_s.set_preempted()
            success = False
            done()
            break
        elif state_ == 0:
            feedback.stat = "Fixing the yaw"
            act_s.publish_feedback(feedback)
            fix_yaw(desired_position)
        elif state_ == 1:
            feedback.stat = "Reaching the target"
            act_s.publish_feedback(feedback)
            go_straight_ahead(desired_position)
        elif state_ == 2:
            feedback.stat = "Angle aligned"
            act_s.publish_feedback(feedback)
            fix_final_yaw(des_yaw)
        elif state_ == 3:
            feedback.stat = "Target reached!"
            act_s.publish_feedback(feedback)
            done()
            break
        else:
            rospy.logerr('Unknown state!')

        rate.sleep()
    if success:
        rospy.loginfo('Goal: Succeeded!')
        result.ok= True
        act_s.set_succeeded(result)


##
#
# This is the main function in which we initialize the node and create a publisher, a subscriber
# and an action server.
#

def main():

    global pub_, act_s
    rospy.init_node('go_to_point')
    pub_ = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
    sub_odom = rospy.Subscriber('/odom', Odometry, clbk_odom)
    act_s = actionlib.SimpleActionServer('/go_to_point', rt2_assignment1.msg.TargetAction, go_to_point, auto_start=False)
    act_s.start()
    rate = rospy.Rate(20)

    while not rospy.is_shutdown():
        rate.sleep()

if __name__ == '__main__':
    main()