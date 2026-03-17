#!/usr/bin/env python3
"""Launch Pepper in Gazebo with Nav2 (SLAM Toolbox + DWB planner).

Usage:
  # SLAM (build map while navigating)
  ros2 launch pepper_gazebo_plugin pepper_navigation.launch.py

  # Localisation against existing map
  ros2 launch pepper_gazebo_plugin pepper_navigation.launch.py \
      use_slam:=false map:=/path/to/map.yaml

Arguments:
  gui         – show Gazebo gzclient window (default: false)
  world       – Gazebo .world file (default: naoFoot.world)
  use_slam    – run slam_toolbox instead of AMCL (default: true)
  map         – map YAML for AMCL mode (ignored when use_slam:=true)
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription, TimerAction, GroupAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PythonExpression
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    gui      = LaunchConfiguration('gui',      default='false')
    world_lc = LaunchConfiguration('world',    default='naoFoot.world')
    use_slam = LaunchConfiguration('use_slam', default='true')
    map_yaml = LaunchConfiguration('map',      default='')

    gazebo_ros_pkg        = get_package_share_directory('gazebo_ros')
    pepper_description_pkg = get_package_share_directory('pepper_description')
    pepper_gazebo_pkg     = get_package_share_directory('pepper_gazebo_plugin')
    nav2_bringup_pkg      = get_package_share_directory('nav2_bringup')

    nav2_params_file = os.path.join(pepper_gazebo_pkg, 'config', 'nav2_params.yaml')
    xacro_file = os.path.join(
        pepper_description_pkg, 'urdf',
        'pepper1.0_generated_urdf', 'pepper_robot_CPU_no_arms.xacro',
    )

    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    # ── Gazebo ───────────────────────────────────────────────────────────────
    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_pkg, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={
            'world': [os.path.join(pepper_gazebo_pkg, 'worlds/'), world_lc],
            'verbose': 'false',
        }.items(),
    )

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_pkg, 'launch', 'gzclient.launch.py')
        ),
        condition=IfCondition(gui),
    )

    # ── Robot description & spawn ─────────────────────────────────────────────
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
        output='screen',
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=['-entity', 'pepper_MP', '-topic', 'robot_description',
                   '-x', '0.0', '-y', '0.0', '-z', '0.05'],
        output='screen',
    )

    # ── Controllers ───────────────────────────────────────────────────────────
    joint_state_broadcaster_spawner = TimerAction(period=8.0, actions=[Node(
        package='controller_manager', executable='spawner',
        arguments=['joint_state_broadcaster'], output='screen',
    )])

    # ── Pepper sensor nodes ───────────────────────────────────────────────────
    laser_publisher     = Node(package='pepper_gazebo_plugin',
                               executable='laser_publisher.py',
                               name='laser_publisher', output='screen')
    odom_publisher      = Node(package='pepper_gazebo_plugin',
                               executable='odom_publisher.py',
                               name='odom_publisher', output='screen')
    velocity_controller = Node(package='pepper_gazebo_plugin',
                               executable='velocity_controller.py',
                               name='velocity_controller', output='screen')

    # ── Nav2 bringup (SLAM mode) ──────────────────────────────────────────────
    nav2_slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_pkg, 'launch', 'bringup_launch.py')
        ),
        condition=IfCondition(use_slam),
        launch_arguments={
            'use_sim_time': 'true',
            'slam': 'true',
            'params_file': nav2_params_file,
            'use_composition': 'false',
        }.items(),
    )

    # ── Nav2 bringup (AMCL / localisation mode) ───────────────────────────────
    nav2_amcl = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_pkg, 'launch', 'bringup_launch.py')
        ),
        condition=UnlessCondition(use_slam),
        launch_arguments={
            'use_sim_time': 'true',
            'slam': 'false',
            'map': map_yaml,
            'params_file': nav2_params_file,
            'use_composition': 'false',
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument('gui',      default_value='false',
                              description='Show Gazebo gzclient'),
        DeclareLaunchArgument('world',    default_value='naoFoot.world',
                              description='World file name (relative to worlds/)'),
        DeclareLaunchArgument('use_slam', default_value='true',
                              description='Run SLAM Toolbox (true) or AMCL (false)'),
        DeclareLaunchArgument('map',      default_value='',
                              description='Map YAML path for AMCL mode'),
        gzserver,
        gzclient,
        robot_state_publisher,
        spawn_entity,
        joint_state_broadcaster_spawner,
        laser_publisher,
        odom_publisher,
        velocity_controller,
        nav2_slam,
        nav2_amcl,
    ])
