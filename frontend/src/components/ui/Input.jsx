export default function Input({ label, error, className = '', ...props }) {
  return (
    <div className="space-y-1">
      {label && <label className="block text-sm font-medium text-text-secondary">{label}</label>}
      <input
        className={`w-full px-3 py-2 rounded-lg border bg-surface text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary-300 focus:border-primary-400 transition ${
          error ? 'border-danger' : 'border-border'
        } ${className}`}
        {...props}
      />
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}
