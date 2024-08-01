import asyncio
from aiohttp import web
from rplidar import RPLidar, RPLidarException
import json
import threading
import time

# LiDAR cihazı ve verileri için global değişkenler
lidar = RPLidar('/dev/ttyUSB0', 115200, 5, None)
scan_data = []
data_lock = threading.Lock()  # threading.Lock kullanıyoruz


def process_lidar_data_sync():
    global scan_data
    try:
        for scan in lidar.iter_scans():
            one_sent = False
            last_angle = None
            temp_scan_data = []
            for d in scan:
                angle = d[1]
                distance = d[2]
                if 20 <= angle <= 160:

                    temp_scan_data.append({'angle': angle, 'distance': distance})

                if last_angle is not None and angle < last_angle:
                    with data_lock:
                        scan_data = temp_scan_data.copy()
                        temp_scan_data = []
                last_angle = d[1]


            one_sent = False
            for d in scan:
                angle = d[1]
                distance = d[2]
                if 80 <= angle <= 100:
                    if (distance / 10) <= 100:
                        one_sent = True
                        print(1)
                        # send_data_to_arduino(1)
                        break
                    else:
                        one_sent = False
                if not one_sent:
                    print(0)
                # send_data_to_arduino(0)

            time.sleep(0.1)  # Veri okuma sıklığı
    except RPLidarException as err:
        print(err)
    except KeyboardInterrupt:
        print('Keyboard interrupt')
    finally:
        lidar.stop()
        lidar.stop_motor()
        lidar.disconnect()

async def handle_request(request):
    with data_lock:  # threading.Lock kullanarak kilidi edin
        response_body = json.dumps(scan_data).encode('utf-8')
        scan_data.clear()  # Verileri temizle
    return web.Response(body=response_body, content_type='application/json')

async def main():
    # LiDAR cihazını başlat
    lidar.connect()
    info = lidar.get_info()
    print(info)
    health = lidar.get_health()
    print(health)

    # Web sunucusunu başlat
    app = web.Application()
    app.router.add_get('/', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 9000)
    await site.start()

    # LiDAR veri işleme görevini başlat
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, process_lidar_data_sync)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Program interrupted')