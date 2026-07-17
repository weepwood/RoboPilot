cmake_minimum_required(VERSION 3.8)
project(robopilot_sim)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config launch rviz urdf worlds
  DESTINATION share/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(
    test_robot_description
    test/test_robot_description.py
    TIMEOUT 30
  )
endif()

ament_package()
