import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler
from core.handle.receiveAudioHandle import startToChat
import json

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict, ws_server=None):
        self.config = config
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.ws_server = ws_server  # 新增，便于查找conn

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def temperature_alert_handler(self, request):
        try:
            data = await request.json()
            device_id = request.headers.get("device-id") or data.get("device_id")
            value = data.get("value")
            event = data.get("event")
            # 打印当前所有在线设备的device-id
            if self.ws_server:
                device_list = [getattr(handler, "device_id", None) for handler in getattr(self.ws_server, "active_connections", [])]
                self.logger.bind(tag=TAG).info(f"当前在线设备列表: {device_list}")
            # 查找conn对象
            conn = None
            if self.ws_server and device_id:
                for handler in getattr(self.ws_server, "active_connections", []):
                    if getattr(handler, "device_id", None) == device_id:
                        conn = handler
                        break
            if not conn:
                return web.json_response({"status": "error", "msg": "未找到设备连接"}, status=404)
            # 构造事件描述
            event_text = f"温度传感器检测到水温为{value}度，已经超过安全饮用温度，请用一句温馨的话提醒用户。"
            await startToChat(conn, event_text)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"status": "error", "msg": str(e)}, status=500)

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            app = web.Application()

            read_config_from_api = server_config.get("read_config_from_api", False)

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.post("/xiaozhi/temperature_alert", self.temperature_alert_handler),
                ]
            )

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次
