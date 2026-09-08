import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { FolderOpen, Tag } from 'lucide-react';
import type { ExtractedTopic } from '../../types/api';
import { Badge, Skeleton } from '../common';
import { CustomChartTooltip } from './CustomChartTooltip';

interface TopicEmergenceChartProps {
  topics: ExtractedTopic[];
  loading: boolean;
}

export const TopicEmergenceChart: React.FC<TopicEmergenceChartProps> = ({
  topics,
  loading,
}) => {
  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', height: '100%', justifyContent: 'center' }}>
        <Skeleton height="2rem" />
        <Skeleton height="3rem" />
        <Skeleton height="3rem" />
      </div>
    );
  }

  if (!topics || topics.length === 0) {
    return (
      <div
        style={{
          height: '220px',
          border: '1px dashed var(--border-muted)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '1.5rem',
          textAlign: 'center',
        }}
      >
        <FolderOpen size={32} color="var(--text-muted)" style={{ marginBottom: '0.5rem', opacity: 0.6 }} />
        <h4 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
          No Thematic Clusters Extracted
        </h4>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', maxWidth: '300px' }}>
          Run topic modeling to cluster posts into emergent narratives and keyword groups.
        </p>
      </div>
    );
  }

  const topTopics = topics.slice(0, 5);

  const chartData = topTopics.map((topic) => {
    // Truncate long labels for chart axis
    const maxLen = 16;
    const shortLabel =
      topic.label.length > maxLen ? `${topic.label.substring(0, maxLen)}...` : topic.label;

    return {
      name: topic.label,
      shortLabel,
      posts: topic.post_count,
      cohesion: Math.round(topic.confidence * 100),
      keywords: topic.keywords,
    };
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      {/* Top 5 Topics Volume Chart */}
      <div style={{ width: '100%', height: '140px' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 0, right: 30, left: 10, bottom: 0 }}
          >
            <defs>
              <linearGradient id="topicPurpleGradient" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#00d2ff" />
              </linearGradient>
            </defs>

            <XAxis
              type="number"
              stroke="var(--text-muted)"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'var(--border-subtle)' }}
            />

            <YAxis
              type="category"
              dataKey="shortLabel"
              stroke="var(--text-secondary)"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              width={95}
            />

            <Tooltip
              content={
                <CustomChartTooltip
                  formatter={(val, _name, item) => {
                    const cohesion = item.payload?.cohesion;
                    return [`${Number(val).toLocaleString()} posts (${cohesion}% cohesion)`, 'Cluster Volume'];
                  }}
                />
              }
            />

            <Bar
              dataKey="posts"
              name="Posts"
              fill="url(#topicPurpleGradient)"
              radius={[0, 4, 4, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Top Topics Narrative Chips */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        {topTopics.slice(0, 3).map((topic, idx) => (
          <div
            key={topic.topic_id || idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '0.45rem 0.65rem',
              backgroundColor: 'var(--bg-tertiary)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '0.8rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', overflow: 'hidden' }}>
              <Tag size={13} color="var(--accent-purple)" style={{ flexShrink: 0 }} />
              <span
                style={{
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  maxWidth: '170px',
                }}
              >
                {topic.label}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexShrink: 0 }}>
              <span style={{ color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}>
                {topic.post_count} posts
              </span>
              <Badge variant="primary" size="sm">
                {Math.round(topic.confidence * 100)}% Cohesion
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
