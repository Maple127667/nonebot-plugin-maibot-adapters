from nonebot import logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    MessageEvent,
    PrivateMessageEvent,
    GroupMessageEvent,
    PokeNotifyEvent,
    NoticeEvent,
    GroupRecallNoticeEvent,
    FriendRecallNoticeEvent,
)
from maim_message import UserInfo, GroupInfo, Seg ,BaseMessageInfo,MessageBase,FormatInfo,TemplateInfo
from .config import Config
from .util import local_file_to_base64

import httpx
import time



config = Config()

# 定义日志配置

class ChatBot:
    def __init__(self):
        self.bot = None  # bot 实例引用
        self._started = False
        self.fastapi_url =  config.Fastapi_url
        self.client = httpx.AsyncClient(timeout=60)  # 创建异步HTTP客户端

    async def _ensure_started(self):
        """确保所有任务已启动"""
        if not self._started:
            self._started = True


    async def handle_message(self, event: MessageEvent, bot: Bot) -> None:
        """处理收到的消息"""

        self.bot = bot  # 更新 bot 实例
        if isinstance(event, PrivateMessageEvent):
            try:
                user_info = UserInfo(
                    user_id=event.user_id,
                    user_nickname=(await bot.get_stranger_info(user_id=event.user_id, no_cache=True))["nickname"],
                    user_cardname=None,
                    platform=config.platfrom,
                )
            except Exception as e:
                logger.error(f"获取陌生人信息失败: {e}")
                return
            logger.debug(user_info)

            # group_info = GroupInfo(group_id=0, group_name="私聊", platform=config.platfrom)
            group_info = None

        # 处理群聊消息
        else:
            #白名单处理逻辑
            if len(config.allow_group_list) != 0 :
                if event.group_id not in config.group_list:
                    return

            user_info = UserInfo(
                user_id=event.user_id,
                user_nickname=event.sender.nickname,
                user_cardname=event.sender.card or None,
                platform=config.platfrom,
            )
            
            group_info = GroupInfo(group_id=event.group_id, group_name=await bot.get_group_info(group_id = event.group_id,no_cache=True), platform=config.platfrom)


        message_info = BaseMessageInfo(
                platform = 'qq',
                message_id = event.message_id,
                time = int(time.time()),
                group_info = group_info,
                user_info = user_info,
        )
        logger.info (event.get_message())
        message_seg = Seg(
                type = 'text',
                data = event.get_plaintext(),  
        )

        message_base = MessageBase(message_info,message_seg,raw_message=event.get_plaintext())

        await self.message_process(message_base)

    async def handle_notice(self, event: NoticeEvent, bot: Bot) -> None:
        """处理收到的通知"""
        if isinstance(event, PokeNotifyEvent):
            # 戳一戳 通知
            # 不处理其他人的戳戳
            if not event.is_tome():
                return

            #白名单处理逻辑
            if len(config.allow_group_list) != 0 :
                if event.group_id not in config.group_list:
                    return



            raw_message = f"[戳了戳]{config.Nickname}"  # 默认类型
            if info := event.model_extra["raw_info"]:
                poke_type = info[2].get("txt", "戳了戳")  # 戳戳类型，例如“拍一拍”、“揉一揉”、“捏一捏”
                custom_poke_message = info[4].get("txt", "")  # 自定义戳戳消息，若不存在会为空字符串
                raw_message = f"[{poke_type}]{config.Nickname}{custom_poke_message}"

                raw_message += "（这是一个类似摸摸头的友善行为，而不是恶意行为，请不要作出攻击发言）"

            user_info = UserInfo(
                user_id=event.user_id,
                user_nickname=(await bot.get_stranger_info(user_id=event.user_id, no_cache=True))["nickname"],
                user_cardname=None,
                platform=config.platfrom,
            )

            if event.group_id:
                group_info = GroupInfo(group_id=event.group_id, group_name=await bot.get_group_info(group_id = event.group_id,no_cache=True), platform=config.platfrom)
            else:
                group_info = None

            message_info = BaseMessageInfo(
                    platform = 'qq',
                    message_id = None,
                    time = int(time.time()),
                    group_info= group_info,
                    user_info = user_info,
            )

            message_seg = Seg(
                    type = 'text',
                    data = raw_message,  
            )

            message_base = MessageBase(message_info,message_seg,raw_message=raw_message)

            await self.message_process(message_base)

        # 处理撤回消息存储的逻辑，先放着不动
        # elif isinstance(event, GroupRecallNoticeEvent) or isinstance(event, FriendRecallNoticeEvent):
        #     user_info = UserInfo(
        #         user_id=event.user_id,
        #         user_nickname=get_user_nickname(event.user_id) or None,
        #         user_cardname=get_user_cardname(event.user_id) or None,
        #         platform=config.platfrom,
        #     )

        #     if isinstance(event, GroupRecallNoticeEvent):
        #         group_info = GroupInfo(group_id=event.group_id, group_name=None, platform=config.platfrom)
        #     else:
        #         group_info = None

        #     chat = await chat_manager.get_or_create_stream(
        #         platform=user_info.platform, user_info=user_info, group_info=group_info
        #     )

        #     await self.storage.store_recalled_message(event.message_id, time.time(), chat)

    async def handle_image_message(self, event: MessageEvent, bot: Bot) -> None:
        """修复后的图片消息处理器"""
        self.bot = bot
        
        #白名单处理逻辑
        if len(config.allow_group_list) != 0 :
            if event.group_id not in config.group_list:
                return


        # 公共信息处理（移到循环外）
        try:
            if isinstance(event, PrivateMessageEvent):
                user_info = UserInfo(
                    user_id=event.user_id,
                    user_nickname=(await bot.get_stranger_info(user_id=event.user_id))["nickname"],
                    user_cardname=None,
                    platform= config.platfrom
                )
                group_info = None
            else:
                user_info = UserInfo(
                    user_id=event.user_id,
                    user_nickname=event.sender.nickname,
                    user_cardname=event.sender.card or None,
                    platform= config.platfrom
                )
                # 获取群信息添加默认值

                group_info = GroupInfo(group_id=event.group_id, group_name=await bot.get_group_info(group_id = event.group_id,no_cache=True), platform=config.platfrom)

        except Exception as e:
            logger.error(f"基础信息获取失败: {e}")
            return

        # 处理图片段
        for segment in event.message:
            if segment.type != "image":
                continue  # 跳过非图片段
            
            # 获取真实图片数据（根据协议适配器实现）
            image_file = segment.data.get("file")
            image_data = await bot.get_image(file=image_file)
            file_path = image_data["file"]
            base64_str = local_file_to_base64(file_path)
            logger.info(f"{base64_str}")

            
            message_seg = Seg(
                type="image",
                data= base64_str
            )
            message_info = BaseMessageInfo(
                platform = config.platfrom,
                message_id = event.message_id,
                time = int(time.time()),
                group_info= group_info,
                user_info = user_info,
        )
            message_base = MessageBase(message_info,message_seg,raw_message="")   
            
            await self.message_process(message_base)
                



    async def handle_forward_message(self, event: MessageEvent, bot: Bot) -> None:
        """专用于处理合并转发的消息处理器"""

        #白名单处理逻辑
        if len(config.allow_group_list) != 0 :
            if event.group_id not in config.group_list:
                return


        # 获取合并转发消息的详细信息
        forward_info = await bot.get_forward_msg(message_id=event.message_id)
        messages = forward_info["messages"]

        # 构建合并转发消息的文本表示
        processed_messages = []
        
        for node in messages:
            # 提取发送者昵称
            nickname = node["sender"].get("nickname", "未知用户")

            # 递归处理消息内容
            message_content = await self.process_message_segments(node["message"], layer=0)

            # 拼接为【昵称】+ 内容
            processed_messages.append(f"【{nickname}】{message_content}")

        # 组合所有消息
        combined_message = "\n".join(processed_messages)
        combined_message = f"合并转发消息内容：\n{combined_message}"

        # 构建用户信息（使用转发消息的发送者）
        user_info = UserInfo(
            user_id=event.user_id,
            user_nickname=event.sender.nickname,
            user_cardname=event.sender.card if hasattr(event.sender, "card") else None,
            platform= config.platfrom,
        )

        # 构建群聊信息（如果是群聊）
        group_info = None
        if isinstance(event, GroupMessageEvent):
            group_info = GroupInfo(group_id=event.group_id, group_name=None, platform=config.platfrom)

        # 创建消息对象
        message_info = BaseMessageInfo(
                platform = config.platfrom,
                message_id = event.message_id,
                time = int(time.time()),
                group_info= group_info,
                user_info = user_info,
        )
        logger.info (event.get_message())
        message_seg = Seg(
                type = 'text',
                data = combined_message,  
        )

        message_base = MessageBase(message_info,message_seg,raw_message=combined_message)

        # 进入标准消息处理流程
        await self.message_process(message_base)

    async def process_message_segments(self, segments: list, layer: int) -> str:
        """递归处理消息段"""
        parts = []
        for seg in segments:
            part = await self.process_segment(seg, layer + 1)
            parts.append(part)
        return "".join(parts)

    async def process_segment(self, seg: dict, layer: int) -> str:
        """处理单个消息段"""
        seg_type = seg["type"]
        if layer > 3:
            # 防止有那种100层转发消息炸飞麦麦
            return "【转发消息】"
        if seg_type == "text":
            return seg["data"]["text"]
        elif seg_type == "image":
            return "[图片]"
        elif seg_type == "face":
            return "[表情]"
        elif seg_type == "at":
            return f"@{seg['data'].get('qq', '未知用户')}"
        elif seg_type == "forward":
            # 递归处理嵌套的合并转发消息
            nested_nodes = seg["data"].get("content", [])
            nested_messages = []
            nested_messages.append("合并转发消息内容：")
            for node in nested_nodes:
                nickname = node["sender"].get("nickname", "未知用户")
                content = await self.process_message_segments(node["message"], layer=layer)
                # nested_messages.append('-' * layer)
                nested_messages.append(f"{'--' * layer}【{nickname}】{content}")
            # nested_messages.append(f"{'--' * layer}合并转发第【{layer}】层结束")
            return "\n".join(nested_messages)
        else:
            return f"[{seg_type}]"


    async def message_process(self, message_base: MessageBase) -> None:

        payload = message_base.to_dict()
        
        logger.info("消息发送成功")

        response = await self.client.post(
            self.fastapi_url,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        # 检查响应状态
        if response.status_code != 200:
            logger.error(f"FastAPI返回错误状态码: {response.status_code}")
            logger.debug(f"响应内容: {response.text}")
        else:
            response_data = response.json()
            logger.success(f"收到服务端响应: {response_data}")
            logger.debug(f"响应内容: {response_data}")
        

# 创建全局ChatBot实例
chat_bot = ChatBot()
