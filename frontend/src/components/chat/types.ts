import type { AgentEvent } from '../../types';

export type MergedTimelineItem = 
  | { kind: 'event'; event: AgentEvent }
  | { kind: 'event_group'; tool_name: string; count: number; raw_events: AgentEvent[] };

// 思考过程内部的有序片段：思考文字 或 工具调用组
export type ThinkingSegment =
  | { kind: 'text'; content: string }
  | { kind: 'tools'; items: MergedTimelineItem[] };

export type TimelineChunk = 
  | { type: 'text';     content: string; id: string }
  | { type: 'thinking'; content: string; id: string; segments?: ThinkingSegment[] }
  | { type: 'tools';    items: MergedTimelineItem[]; id: string; raw_count: number };
