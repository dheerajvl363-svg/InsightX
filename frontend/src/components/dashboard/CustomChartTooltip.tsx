import React from 'react';

export interface TooltipPayloadItem {
  name?: string;
  value?: number | string;
  color?: string;
  fill?: string;
  dataKey?: string;
  payload?: Record<string, unknown>;
}

export interface CustomChartTooltipProps {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
  title?: string;
  formatter?: (value: number | string, name: string, item: TooltipPayloadItem) => [string, string];
  labelFormatter?: (label: string) => string;
}

export const CustomChartTooltip: React.FC<CustomChartTooltipProps> = ({
  active,
  payload,
  label,
  title,
  formatter,
  labelFormatter,
}) => {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const displayTitle = title || (label !== undefined && label !== null ? (labelFormatter ? labelFormatter(label) : String(label)) : '');

  return (
    <div
      style={{
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '0.65rem 0.85rem',
        boxShadow: 'var(--shadow-lg)',
        backdropFilter: 'blur(12px)',
        minWidth: '160px',
        maxWidth: '280px',
        zIndex: 50,
      }}
    >
      {displayTitle && (
        <div
          style={{
            fontSize: '0.78rem',
            fontWeight: 600,
            color: 'var(--text-secondary)',
            marginBottom: '0.4rem',
            paddingBottom: '0.35rem',
            borderBottom: '1px solid var(--border-subtle)',
          }}
        >
          {displayTitle}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        {payload.map((item, idx) => {
          const itemColor = item.color || item.fill || 'var(--accent-cyan)';
          const itemName = item.name || String(item.dataKey || 'Value');
          const rawValue = item.value ?? 0;
          const [formattedValue, formattedName] = formatter
            ? formatter(rawValue, itemName, item)
            : [typeof rawValue === 'number' ? rawValue.toLocaleString() : String(rawValue), itemName];

          return (
            <div
              key={`item-${idx}`}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '0.75rem',
                fontSize: '0.8rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                <span
                  style={{
                    width: '8px',
                    height: '8px',
                    borderRadius: 'var(--radius-full)',
                    backgroundColor: itemColor,
                    display: 'inline-block',
                    flexShrink: 0,
                  }}
                />
                <span style={{ color: 'var(--text-secondary)' }}>{formattedName}</span>
              </div>
              <span
                style={{
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                {formattedValue}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
