cmake_minimum_required(VERSION 3.8)
project(zsl1_world VERSION 3.0.0)

find_package(ament_cmake REQUIRED)

foreach(dir launch worlds models)
    if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${dir})
        install(
            DIRECTORY ${dir}/
            DESTINATION share/${PROJECT_NAME}/${dir}
        )
    endif()
endforeach()

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()

