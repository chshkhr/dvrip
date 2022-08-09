# https://pypi.org/project/hikvisionapi/
from hikvisionapi import Client

cam = Client('http://192.168.0.107', 'vlad', 'Vlad37650')

# # Dict response (default)
response = cam.System.deviceInfo(method='get')
print(response)
#
# # xml text response
# response = cam.System.deviceInfo(method='get', present='text')
# print(response)

# print(response)motion_detection_info = cam.System.Video.inputs.channels[1].motionDetection(method='get')
# print(motion_detection_info)

# cam.count_events = 2  # The number of events we want to retrieve (default = 1)
# response = cam.Event.notification.alertStream(method='get', type='stream')
# print(response)

