"""Stream Processor - Real-time streaming analytics"""

from typing import Dict, Any, Optional, AsyncIterator
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StreamEvent:
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    sequence: int


class StreamProcessor:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.sequence_counter = 0
        logger.info("StreamProcessor initialized")
    
    async def stream_analysis(self, analysis_id: str, interval_ms: int = 100) -> AsyncIterator[StreamEvent]:
        queue = asyncio.Queue()
        self.active_streams[analysis_id] = queue
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=interval_ms / 1000.0)
                    if event is None:
                        break
                    yield event
                except asyncio.TimeoutError:
                    yield StreamEvent(
                        event_type='heartbeat',
                        data={'status': 'active'},
                        timestamp=datetime.utcnow(),
                        sequence=self._next_sequence()
                    )
        finally:
            self.active_streams.pop(analysis_id, None)
    
    async def publish_progress(self, analysis_id: str, progress: float, stage: str, metrics: Optional[Dict[str, Any]] = None):
        if analysis_id not in self.active_streams:
            return
        
        event = StreamEvent(
            event_type='progress',
            data={'analysis_id': analysis_id, 'progress': progress, 'stage': stage, 'metrics': metrics or {}},
            timestamp=datetime.utcnow(),
            sequence=self._next_sequence()
        )
        
        await self.active_streams[analysis_id].put(event)
    
    def _next_sequence(self) -> int:
        self.sequence_counter += 1
        return self.sequence_counter
