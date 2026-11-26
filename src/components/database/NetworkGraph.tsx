import { useCallback } from 'react';
import { api, type NetworkData } from '@/lib/api';
import { useAsync } from '@/hooks/useAsync';
import { Card, Notice } from './parts';

const WIDTH = 760;
const HEIGHT = 480;

function wrap(name: string): string[] {
  const words = name.split(' ');
  const out = [''];
  for (const word of words) {
    const last = out[out.length - 1];
    if (last && `${last} ${word}`.length > 17) out.push(word);
    else out[out.length - 1] = last ? `${last} ${word}` : word;
  }
  return out.slice(0, 3);
}

function Drawing({ data }: { data: NetworkData }) {
  const others = data.edges.map((edge, index) => {
    const angle = (index / data.edges.length) * Math.PI * 2 - Math.PI / 2;
    return {
      edge,
      node: data.nodes.find((n) => n.id === edge.target)!,
      x: WIDTH / 2 + Math.cos(angle) * 290,
      y: HEIGHT / 2 + Math.sin(angle) * 180,
    };
  });
  const label = (x: number, y: number, name: string, fill: string) => {
    const lines = wrap(name);
    return (
      <text x={x} y={y - (lines.length - 1) * 7} textAnchor="middle" dominantBaseline="middle" fontSize="12.5" fill={fill} className="font-mono2">
        {lines.map((line, i) => (
          <tspan key={line} x={x} dy={i === 0 ? 0 : 14}>{line}</tspan>
        ))}
      </text>
    );
  };
  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full min-w-[560px]"
      role="img"
      aria-label={`Substitution links from ${data.center_name} to ${others.map((o) => o.node.name).join(', ')}`}
    >
      {others.map(({ edge, x, y }) => (
        <g key={edge.target}>
          <line
            x1={WIDTH / 2} y1={HEIGHT / 2} x2={x} y2={y}
            stroke="#a39b8b" strokeWidth={1 + edge.weight * 5} opacity={0.6}
            strokeDasharray={edge.role_score < 1 ? '6 6' : undefined}
          />
          <text
            x={WIDTH / 2 + (x - WIDTH / 2) * 0.55} y={HEIGHT / 2 + (y - HEIGHT / 2) * 0.55}
            textAnchor="middle" fontSize="11" fill="#fdfdfd" className="font-mono2"
            stroke="#4a463e" strokeWidth="4" paintOrder="stroke"
          >
            {edge.flavor_jaccard === null ? 'no data' : edge.flavor_jaccard.toFixed(2)}
          </text>
        </g>
      ))}
      {others.map(({ node, x, y }) => (
        <g key={node.id}>
          <ellipse cx={x} cy={y} rx="68" ry="32" fill="#efede9" />
          {label(x, y, node.name, '#3e3a32')}
        </g>
      ))}
      <ellipse cx={WIDTH / 2} cy={HEIGHT / 2} rx="78" ry="38" fill="#f26522" />
      {label(WIDTH / 2, HEIGHT / 2, data.center_name, '#fdfdfd')}
    </svg>
  );
}

export default function NetworkGraph({ ingredientId, region }: { ingredientId: string; region: string }) {
  const network = useAsync(
    useCallback((signal: AbortSignal) => api.network(ingredientId, region, signal), [ingredientId, region]),
  );
  const data = network.data?.center === ingredientId ? network.data : null;
  return (
    <Card
      title="Substitution network"
      aside={
        data && (
          <span className="font-mono2 text-[10px] text-[#a39b8b]">
            strongest {data.edges.length} of {data.total_neighbours} links
          </span>
        )
      }
    >
      {network.error && (
        <div className="mt-4"><Notice tone="warn">{network.error}</Notice></div>
      )}
      {network.loading && <p className="mt-4 font-mono2 text-[11px] text-[#a39b8b]">Loading the network…</p>}
      {data && data.edges.length === 0 && (
        <p className="mt-4 font-body text-[14px] text-[#efede9]/75">This ingredient has no substitution links.</p>
      )}
      {data && data.edges.length > 0 && (
        <div className="mt-3 overflow-x-auto">
          <Drawing data={data} />
        </div>
      )}
      <p className="mt-2 font-body text-[13px] text-[#a39b8b]">
        A link means the cooking roles are compatible (solid: same role, dashed: related). The number is FlavorDB2
        flavor similarity (“no data” if a profile is missing or too thin) and thicker lines combine both. A link does not mean a swap is healthier; the ranking above
        decides that.
      </p>
    </Card>
  );
}
