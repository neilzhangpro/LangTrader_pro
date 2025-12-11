from typing import Dict, Callable, List, Optional
from collections import defaultdict
from utils.logger import logger

import websockets
import asyncio
import json

class WSClient:
    """统一的WebSocket客户端 - 用于实时数据流推送"""
    
    def __init__(self, base_url: str = "wss://fstream.binance.com/ws") -> None:
        # 改为使用 /ws 端点，支持动态订阅
        self.base_url = base_url
        self.conn: Optional[websockets.WebSocketClientProtocol] = None
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.reconnect = True
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._subscribed_streams: List[str] = []
        self._reconnect_delay = 5  # 重连延迟（秒）
        self._max_reconnect_delay = 60
        self._request_id = 0  # 请求ID计数器
        
        # WebSocket 连接配置
        self._open_timeout = 30.0  # 连接建立超时：30秒
        self._close_timeout = 10.0  # 关闭连接超时：10秒
        self._ping_interval = 20.0  # 每20秒发送一次ping（保持连接）
        self._ping_timeout = 10.0  # ping响应超时：10秒
        self._recv_timeout = 60.0  # 接收消息超时：60秒
        self._heartbeat_interval = 20.0  # 心跳间隔：20秒
        
    def _get_next_id(self) -> int:
        """获取下一个请求ID"""
        self._request_id += 1
        return self._request_id
        
    async def connect(self):
        """建立WebSocket连接"""
        # 如果连接已存在且有效，直接返回
        if self.conn is not None:
            try:
                # 检查连接是否仍然有效（发送ping）
                pong_waiter = await self.conn.ping()
                await asyncio.wait_for(pong_waiter, timeout=5.0)
                logger.debug("WebSocket连接仍然有效")
                return
            except Exception:
                # 连接无效，需要重新连接
                logger.warning("检测到无效连接，将重新连接")
                self.conn = None
            
        try:
            # 添加连接超时和保活机制
            self.conn = await asyncio.wait_for(
                websockets.connect(
                    self.base_url,
                    close_timeout=self._close_timeout,
                    ping_interval=self._ping_interval,
                    ping_timeout=self._ping_timeout,
                ),
                timeout=self._open_timeout
            )
            logger.info(f"✅ WebSocket连接已建立: {self.base_url}")
            
            # 重新订阅之前的流
            if self._subscribed_streams:
                await self._resubscribe()
                
        except asyncio.TimeoutError:
            logger.error(f"❌ WebSocket连接超时: {self.base_url} (超时时间: {self._open_timeout}秒)")
            self.conn = None
            raise
        except Exception as e:
            logger.error(f"❌ WebSocket连接失败: {e}", exc_info=True)
            self.conn = None
            raise
    
    async def _resubscribe(self):
        """重新订阅之前的流"""
        if not self._subscribed_streams:
            return
            
        subscribe_msg = {
            "method": "SUBSCRIBE",
            "params": self._subscribed_streams,
            "id": self._get_next_id()
        }
        await self.conn.send(json.dumps(subscribe_msg))
        logger.info(f"重新订阅流: {self._subscribed_streams}")
    
    async def subscribe(self, stream: str, callback: Callable):
        """订阅数据流"""
        if stream not in self._subscribed_streams:
            self._subscribed_streams.append(stream)
            
        self.subscribers[stream].append(callback)
        
        if self.conn is not None:
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [stream],
                "id": self._get_next_id()
            }
            await self.conn.send(json.dumps(subscribe_msg))
            logger.info(f"订阅流: {stream}")
    
    async def unsubscribe(self, stream: str, callback: Optional[Callable] = None):
        """取消订阅数据流"""
        if callback:
            if stream in self.subscribers:
                self.subscribers[stream].remove(callback)
        else:
            self.subscribers.pop(stream, None)
        
        if stream in self._subscribed_streams:
            self._subscribed_streams.remove(stream)
            
        if self.conn is not None:
            unsubscribe_msg = {
                "method": "UNSUBSCRIBE",
                "params": [stream],
                "id": self._get_next_id()
            }
            await self.conn.send(json.dumps(unsubscribe_msg))
            logger.info(f"取消订阅流: {stream}")
    
    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            
            # 处理订阅确认消息
            if "result" in data and "id" in data:
                if data["result"] is None:
                    logger.debug(f"订阅确认: {data}")
                else:
                    logger.warning(f"订阅响应: {data}")
                return
            
            # Binance WebSocket 数据消息格式（使用 /ws 端点时的格式）
            # 格式1: 直接的数据对象（单一流）
            if "e" in data:  # 事件类型字段
                # 这是单一流的数据格式
                stream_name = f"{data.get('s', '').lower()}@{data.get('e', '').lower()}"
                # 根据事件类型构建流名称
                if data.get("e") == "kline":
                    stream_name = f"{data.get('s', '').lower()}@kline_{data.get('k', {}).get('i', '')}"
                elif data.get("e") == "24hrTicker":
                    stream_name = f"{data.get('s', '').lower()}@ticker"
                
                if stream_name in self.subscribers:
                    for callback in self.subscribers[stream_name]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(data)
                            else:
                                callback(data)
                        except Exception as e:
                            logger.error(f"回调函数执行失败: {e}", exc_info=True)
                return
            
            # 格式2: 组合流格式 {"stream": "...", "data": {...}}
            if "stream" in data and "data" in data:
                stream = data["stream"]
                payload = data["data"]
                
                # 通知所有订阅者
                if stream in self.subscribers:
                    for callback in self.subscribers[stream]:
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(payload)
                            else:
                                callback(payload)
                        except Exception as e:
                            logger.error(f"回调函数执行失败: {e}", exc_info=True)
                return
            
            # 未知格式，记录日志
            logger.debug(f"收到未知格式消息: {data}")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}, 消息: {message}")
        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
    
    async def _heartbeat_loop(self):
        """心跳循环 - 定期发送 ping 保持连接活跃"""
        while self._running:
            try:
                await asyncio.sleep(self._heartbeat_interval)
                
                if not self._running:
                    break
                    
                if self.conn is None:
                    logger.debug("连接不存在，跳过心跳")
                    continue
                
                # 发送 WebSocket ping 帧（应用层）
                try:
                    await self.conn.ping()
                    logger.debug("✓ 心跳 ping 已发送")
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("心跳发送失败：连接已关闭")
                    self.conn = None
                except Exception as e:
                    logger.warning(f"心跳发送失败: {e}")
                    # 如果 ping 失败，标记连接为无效
                    self.conn = None
                    
            except asyncio.CancelledError:
                logger.debug("心跳循环已取消")
                break
            except Exception as e:
                logger.error(f"心跳循环错误: {e}", exc_info=True)
                await asyncio.sleep(5)  # 出错后等待5秒再继续
    
    async def _listen(self):
        """监听WebSocket消息（带超时机制）"""
        while self._running:
            try:
                if self.conn is None:
                    await self.connect()
                
                # 添加超时机制，避免无限等待
                try:
                    message = await asyncio.wait_for(
                        self.conn.recv(),
                        timeout=self._recv_timeout
                    )
                    await self._handle_message(message)
                except asyncio.TimeoutError:
                    # 超时后发送 ping 检查连接状态
                    logger.debug(f"接收消息超时（{self._recv_timeout}秒），检查连接状态")
                    if self.conn is not None:
                        try:
                            await self.conn.ping()
                            logger.debug("连接状态正常，继续监听")
                            continue
                        except websockets.exceptions.ConnectionClosed:
                            logger.warning("ping 失败：连接已关闭")
                            self.conn = None
                            if self.reconnect:
                                await self._reconnect()
                            continue
                        except Exception as e:
                            logger.warning(f"ping 失败: {e}，连接可能已断开")
                            self.conn = None
                            if self.reconnect:
                                await self._reconnect()
                            continue
                    else:
                        # 连接为 None，尝试重连
                        if self.reconnect:
                            await self._reconnect()
                        continue
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket连接已关闭")
                self.conn = None
                if self.reconnect:
                    await self._reconnect()
                else:
                    break
                    
            except Exception as e:
                logger.error(f"监听消息时出错: {e}", exc_info=True)
                self.conn = None
                if self.reconnect:
                    await self._reconnect()
                else:
                    break
    
    async def _reconnect(self):
        """自动重连（带重试限制）"""
        delay = self._reconnect_delay
        retry_count = 0
        max_retries = 10  # 最大重试次数
        
        while self._running and self.reconnect and retry_count < max_retries:
            try:
                logger.info(f"等待 {delay} 秒后重连... (尝试 {retry_count + 1}/{max_retries})")
                await asyncio.sleep(delay)
                await self.connect()
                logger.info("✅ 重连成功")
                break
            except asyncio.TimeoutError:
                retry_count += 1
                logger.error(f"重连超时 ({retry_count}/{max_retries})")
                if retry_count >= max_retries:
                    logger.error("达到最大重试次数，停止重连")
                    break
                delay = min(delay * 2, self._max_reconnect_delay)
            except Exception as e:
                retry_count += 1
                logger.error(f"重连失败 ({retry_count}/{max_retries}): {e}")
                if retry_count >= max_retries:
                    logger.error("达到最大重试次数，停止重连")
                    break
                delay = min(delay * 2, self._max_reconnect_delay)
    
    async def start(self):
        """启动WebSocket客户端"""
        if self._running:
            return
            
        self._running = True
        await self.connect()
        self._task = asyncio.create_task(self._listen())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket客户端已启动（包含心跳机制）")
    
    async def stop(self):
        """停止WebSocket客户端"""
        self._running = False
        self.reconnect = False
        
        # 停止心跳任务
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
        
        # 停止监听任务
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        # 关闭连接
        if self.conn:
            try:
                await self.conn.close()
            except Exception as e:
                logger.warning(f"关闭连接时出错: {e}")
            self.conn = None
            
        logger.info("WebSocket客户端已停止")
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()