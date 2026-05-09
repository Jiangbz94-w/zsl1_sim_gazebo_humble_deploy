/**
 * gt_odom_tf_publisher.cpp  (ROS2 Humble)
 *
 * Subscribes to a Gazebo ground-truth odometry topic that reports the world
 * pose of a sensor link (e.g. mid360_link or camera_optical_link). Uses the
 * static URDF TF tree (published by robot_state_publisher) to look up the
 * fixed transform from that sensor link to the robot BASE_LINK, then derives
 * and broadcasts:
 *
 *     world  →  <robot_namespace>/BASE_LINK
 *
 * This is what RViz2 needs in order to render the full robot model and all
 * sensor topics with correct world poses.
 *
 * ROS2 parameters:
 *   odometry_topic   (string)  e.g. /zsl1sensor1/mid360_mid/gazebo_gt/odometry
 *   child_frame      (string)  the frame whose pose `odometry_topic` reports,
 *                              e.g. zsl1sensor1/mid360_mid/mid360_link
 *   base_link_frame  (string)  the robot base frame, e.g. zsl1sensor1/BASE_LINK
 *   world_frame      (string)  default "world"
 */

#include <chrono>
#include <memory>
#include <string>

#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <geometry_msgs/msg/transform_stamped.hpp>

#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <tf2_ros/transform_broadcaster.h>
#include <tf2/LinearMath/Transform.h>
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/LinearMath/Vector3.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

class GtOdomTFPublisher : public rclcpp::Node
{
public:
  GtOdomTFPublisher()
  : rclcpp::Node("gt_odom_tf_publisher")
  {
    odometry_topic_ = declare_parameter<std::string>(
        "odometry_topic", "/zsl1sensor1/mid360_mid/gazebo_gt/odometry");
    child_frame_ = declare_parameter<std::string>(
        "child_frame", "zsl1sensor1/mid360_mid/mid360_link");
    base_link_frame_ = declare_parameter<std::string>(
        "base_link_frame", "zsl1sensor1/BASE_LINK");
    world_frame_ = declare_parameter<std::string>(
        "world_frame", "world");

    tf_buffer_ = std::make_shared<tf2_ros::Buffer>(get_clock());
    tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);
    tf_broadcaster_ = std::make_shared<tf2_ros::TransformBroadcaster>(*this);

    rclcpp::QoS qos(rclcpp::KeepLast(10));
    qos.best_effort();  // gazebo_ros_p3d publishes Best-Effort by default
    sub_ = create_subscription<nav_msgs::msg::Odometry>(
        odometry_topic_, qos,
        std::bind(&GtOdomTFPublisher::odometryCb, this, std::placeholders::_1));

    RCLCPP_INFO(get_logger(),
        "started:\n"
        "  odometry_topic : %s\n"
        "  child_frame    : %s\n"
        "  base_link      : %s\n"
        "  world_frame    : %s",
        odometry_topic_.c_str(), child_frame_.c_str(),
        base_link_frame_.c_str(), world_frame_.c_str());
  }

private:
  void odometryCb(const nav_msgs::msg::Odometry::ConstSharedPtr msg)
  {
    const auto & pos = msg->pose.pose.position;
    const auto & ori = msg->pose.pose.orientation;
    tf2::Transform T_world_child(
        tf2::Quaternion(ori.x, ori.y, ori.z, ori.w),
        tf2::Vector3   (pos.x, pos.y, pos.z));

    geometry_msgs::msg::TransformStamped tf_child_to_base;
    try {
      tf_child_to_base = tf_buffer_->lookupTransform(
          child_frame_, base_link_frame_,
          tf2::TimePointZero,
          tf2::durationFromSec(0.5));
    } catch (const tf2::TransformException & ex) {
      auto & clk = *get_clock();
      RCLCPP_WARN_THROTTLE(get_logger(), clk, 5000,
          "tf lookup (%s -> %s) failed: %s",
          child_frame_.c_str(), base_link_frame_.c_str(), ex.what());
      return;
    }

    const auto & tr = tf_child_to_base.transform.translation;
    const auto & ro = tf_child_to_base.transform.rotation;
    tf2::Transform T_child_to_base(
        tf2::Quaternion(ro.x, ro.y, ro.z, ro.w),
        tf2::Vector3   (tr.x, tr.y, tr.z));

    tf2::Transform T_world_base = T_world_child * T_child_to_base;

    geometry_msgs::msg::TransformStamped out;
    out.header.stamp    = msg->header.stamp;
    out.header.frame_id = world_frame_;
    out.child_frame_id  = base_link_frame_;
    const auto & t = T_world_base.getOrigin();
    const auto & q = T_world_base.getRotation();
    out.transform.translation.x = t.x();
    out.transform.translation.y = t.y();
    out.transform.translation.z = t.z();
    out.transform.rotation.x = q.x();
    out.transform.rotation.y = q.y();
    out.transform.rotation.z = q.z();
    out.transform.rotation.w = q.w();
    tf_broadcaster_->sendTransform(out);
  }

  std::string odometry_topic_;
  std::string child_frame_;
  std::string base_link_frame_;
  std::string world_frame_;

  std::shared_ptr<tf2_ros::Buffer>              tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener>   tf_listener_;
  std::shared_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr sub_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<GtOdomTFPublisher>());
  rclcpp::shutdown();
  return 0;
}
