from plugins_func.register import register_function, ToolType, ActionResponse, Action
import json
from loguru import logger
import asyncio

TAG = __name__

get_temperature_function_desc = {
    "type": "function",
    "function": {
        "name": "get_temperature",
        "description": "获取当前水杯的温度信息。用户可以说：现在水温多少、水杯温度、现在的温度等。",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
}

@register_function("get_temperature", get_temperature_function_desc, ToolType.SYSTEM_CTL)
def get_temperature(conn):
    logger.bind(tag=TAG).info("水温查询插件被调用，准备下发查询指令...")
    msg = {
        "type": "iot",
        "commands": [
            {"action": "query_cup_temperature"}
        ]
    }
    try:
        logger.bind(tag=TAG).info(f"准备下发水温查询指令: {msg}")
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(conn.websocket.send(json.dumps(msg, ensure_ascii=False)), loop)
        else:
            loop.run_until_complete(conn.websocket.send(json.dumps(msg, ensure_ascii=False)))
        logger.bind(tag=TAG).info("✅ 水温查询指令下发成功！等待小智端响应...")
        return ActionResponse(Action.REQLLM, "正在为您查询水温...", None)
    except Exception as e:
        logger.bind(tag=TAG).error(f"❌ 水温查询指令下发失败: {e}")
        return ActionResponse(Action.ERROR, f"抱歉，水温查询失败: {e}", None) 