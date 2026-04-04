import { Link } from 'react-router-dom';
import { parseMentions } from '../lib/utils';

export default function MentionText({ text, className = '' }) {
  if (!text) return null;
  const parts = parseMentions(text);
  return (
    <span className={className}>
      {parts.map((part, i) =>
        part.type === 'mention' ? (
          <Link
            key={i}
            to={`/u/${part.value.slice(1)}`}
            className="text-primary-600 font-medium hover:underline"
          >
            {part.value}
          </Link>
        ) : (
          <span key={i}>{part.value}</span>
        )
      )}
    </span>
  );
}
