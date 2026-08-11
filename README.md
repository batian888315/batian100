工作空间

cd \~/competition\_ws

source install/setup.bash



启动底盘

source \~/competition\_ws/install/setup.bash

ros2 launch origincar\_base origincar\_bringup.launch.py



启动雷达

source \~/competition\_ws/install/setup.bash

ros2 run ydlidar\_ros2\_driver ydlidar\_ros2\_driver\_node --ros-args -p port:=/dev/ttyUSB0 -p frame\_id:=laser\_frame -p lidar\_type:=1



启动摄像头

source \~/competition\_ws/install/setup.bash

ros2 run usb\_cam usb\_cam\_node --ros-args -p image\_width:=640 -p image\_height:=480



启动二维码

source \~/competition\_ws/install/setup.bash

ros2 run competition\_control qr\_detector.py



启动图文

source \~/competition\_ws/install/setup.bash

ros2 run competition\_control vision\_to\_text.py



启动

source \~/competition\_ws/install/setup.bash

ros2 run competition\_control competition\_state\_machine.py

