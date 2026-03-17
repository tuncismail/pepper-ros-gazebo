#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    gui = LaunchConfiguration('gui', default='false')

    gazebo_ros_pkg = get_package_share_directory('gazebo_ros')
    pepper_description_pkg = get_package_share_directory('pepper_description')
    pepper_gazebo_pkg = get_package_share_directory('pepper_gazebo_plugin')

    world_file = os.path.join(pepper_gazebo_pkg, 'worlds', 'naoFoot.world')
    xacro_file = os.path.join(
        pepper_description_pkg, 'urdf',
        'pepper1.0_generated_urdf', 'pepper_robot_CPU_no_arms.xacro'
    )

    robot_description = ParameterValue(Command(['xacro ', xacro_file]), value_type=str)

    gzserver = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_pkg, 'launch', 'gzserver.launch.py')
        ),
        launch_arguments={'world': world_file, 'verbose': 'false'}.items(),
    )

    gzclient = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_ros_pkg, 'launch', 'gzclient.launch.py')
        ),
        condition=IfCondition(gui),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
        output='screen',
    )

    spawn_entity = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-entity', 'pepper_MP',
            '-topic', 'robot_description',
            '-x', '-0.5', '-y', '1', '-z', '0.05',
        ],
        output='screen',
    )

    joint_state_broadcaster_spawner = TimerAction(
        period=8.0,
        actions=[Node(
            package='controller_manager',
            executable='spawner',
            arguments=['joint_state_broadcaster'],
            output='screen',
        )]
    )

    head_controller_spawner = TimerAction(
        period=10.0,
        actions=[Node(
            package='controller_manager',
            executable='spawner',
            arguments=['head_controller'],
            output='screen',
        )]
    )

    pelvis_controller_spawner = TimerAction(
        period=10.0,
        actions=[Node(
            package='controller_manager',
            executable='spawner',
            arguments=['pelvis_controller'],
            output='screen',
        )]
    )

    laser_publisher = Node(
        package='pepper_gazebo_plugin',
        executable='laser_publisher.py',
        name='laser_publisher',
        output='screen',
    )

    odom_publisher = Node(
        package='pepper_gazebo_plugin',
        executable='odom_publisher.py',
        name='odom_publisher',
        output='screen',
    )

    velocity_controller = Node(
        package='pepper_gazebo_plugin',
        executable='velocity_controller.py',
        name='velocity_controller',
        output='screen',
    )

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='false',
                              description='Launch Gazebo GUI'),
        DeclareLaunchArgument('headless', default_value='true',
                              description='Run headless'),
        gzserver,
        gzclient,
        robot_state_publisher,
        spawn_entity,
        joint_state_broadcaster_spawner,
        head_controller_spawner,
        pelvis_controller_spawner,
        laser_publisher,
        odom_publisher,
        velocity_controller,
    ])
