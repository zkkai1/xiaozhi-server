import json
import asyncio
import uuid
from core.handle.sendAudioHandle import send_stt_message
from core.handle.helloHandle import checkWakeupWords
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import ContentType
from core.utils.dialogue import Message
from core.providers.tools.device_mcp import call_mcp_tool
from plugins_func.register import Action, ActionResponse
from loguru import logger

TAG = __name__

async def handle_user_intent(conn, text):
    # 检查是否有明确的退出命令
    filtered_text = remove_punctuation_and_length(text)[1]
    logger.bind(tag=TAG).info(f"处理用户意图，原始文本: {text}")
    logger.bind(tag=TAG).info(f"当前意图类型: {conn.intent_type}")
    
    if await check_direct_exit(conn, filtered_text):
        return True
    # 检查是否是唤醒词
    if await checkWakeupWords(conn, filtered_text):
        return True

    # 使用LLM进行意图分析
    logger.bind(tag=TAG).info("开始进行LLM意图分析...")
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        logger.bind(tag=TAG).warning("意图分析返回空结果")
        return False
    # 处理各种意图
    logger.bind(tag=TAG).info(f"意图分析结果: {intent_result}")
    return await process_intent_result(conn, intent_result, text)


async def check_direct_exit(conn, text):
    """检查是否有明确的退出命令"""
    _, text = remove_punctuation_and_length(text)
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            conn.logger.bind(tag=TAG).info(f"识别到明确的退出命令: {text}")
            await send_stt_message(conn, text)
            await conn.close()
            return True
    return False


async def analyze_intent_with_llm(conn, text):
    """使用LLM分析用户意图"""
    if not hasattr(conn, "intent") or not conn.intent:
        conn.logger.bind(tag=TAG).warning("意图识别服务未初始化")
        return None

    # 对话历史记录
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        logger.bind(tag=TAG).info(f"LLM意图识别结果: {intent_result}")
        return intent_result
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"意图识别失败: {str(e)}")

    return None


async def process_intent_result(conn, intent_result, original_text):
    """处理意图识别结果"""
    try:
        # 尝试将结果解析为JSON
        intent_data = json.loads(intent_result)
        logger.bind(tag=TAG).info(f"解析意图数据: {intent_data}")

        # 检查是否有function_call
        if "function_call" in intent_data:
            # 直接从意图识别获取了function_call
            function_name = intent_data["function_call"]["name"]
            logger.bind(tag=TAG).info(f"检测到function_call: {function_name}")

            if function_name == "continue_chat":
                return False

            if function_name == "play_music":
                funcItem = conn.func_handler.get_function(function_name)
                if not funcItem:
                    conn.func_handler.function_registry.register_function("play_music")

            function_args = {}
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
                if function_args is None:
                    function_args = {}
            # 确保参数是字符串格式的JSON
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)
            conn.client_abort = False

            # 使用executor执行函数调用和结果处理
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))

                # 使用统一工具处理器处理所有工具调用
                try:
                    logger.bind(tag=TAG).info(f"开始执行工具调用: {function_name}")
                    result = asyncio.run_coroutine_threadsafe(
                        conn.func_handler.handle_llm_function_call(
                            conn, function_call_data
                        ),
                        conn.loop,
                    ).result()
                    logger.bind(tag=TAG).info(f"工具调用结果: {result}")
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"工具调用失败: {e}")
                    result = ActionResponse(
                        action=Action.ERROR, result=str(e), response=str(e)
                    )

                if result:
                    if result.action == Action.RESPONSE:  # 直接回复前端
                        text = result.response
                        if text is not None:
                            speak_txt(conn, text)
                    elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
                        text = result.result
                        conn.dialogue.put(Message(role="tool", content=text))
                        llm_result = conn.intent.replyResult(text, original_text)
                        if llm_result is None:
                            llm_result = text
                        speak_txt(conn, llm_result)
                    elif (
                        result.action == Action.NOTFOUND
                        or result.action == Action.ERROR
                    ):
                        text = result.result
                        if text is not None:
                            speak_txt(conn, text)
                    elif function_name != "play_music":
                        # For backward compatibility with original code
                        # 获取当前最新的文本索引
                        text = result.response
                        if text is None:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)

            # 将函数执行放在线程池中
            conn.executor.submit(process_function_call)
            return True
        logger.bind(tag=TAG).info("未检测到function_call，继续对话")
        return False
    except json.JSONDecodeError as e:
        conn.logger.bind(tag=TAG).error(f"处理意图结果时出错: {e}")
        return False


def speak_txt(conn, text):
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.dialogue.put(Message(role="assistant", content=text))
