import { getInitials } from '../../lib/utils';

export default function Avatar({ username, avatarUrl, size = 'md' }) {
  const sizes = { sm: 'w-7 h-7 text-xs', md: 'w-9 h-9 text-sm', lg: 'w-12 h-12 text-base' };

  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt={username}
        className={`${sizes[size]} rounded-full object-cover`}
      />
    );
  }

  return (
    <div
      className={`${sizes[size]} rounded-full bg-primary-100 text-primary-700 flex items-center justify-center font-semibold`}
    >
      {getInitials(username)}
    </div>
  );
}
