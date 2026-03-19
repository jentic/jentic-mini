
export function JenticLogo() {
  return (
    <div className="flex items-center gap-2">
      {/* Inline SVG logo — multicoloured eye-like mark */}
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="14" cy="14" r="13" stroke="#7aacaf" strokeWidth="1.5" />
        <circle cx="14" cy="14" r="7" fill="#7aacaf" opacity="0.15" />
        <circle cx="14" cy="14" r="4" fill="#7aacaf" opacity="0.6" />
        <circle cx="14" cy="14" r="2" fill="#79d2b8" />
        {/* Orbit marks */}
        <circle cx="14" cy="3" r="1.2" fill="#f1e38b" />
        <circle cx="14" cy="25" r="1.2" fill="#edadaf" />
        <circle cx="3" cy="14" r="1.2" fill="#68baec" />
        <circle cx="25" cy="14" r="1.2" fill="#fdbd79" />
      </svg>
      <div className="flex items-baseline gap-1">
        <span className="font-heading font-bold text-foreground text-lg">jentic</span>
        <span className="font-mono text-xs text-accent-teal/70 bg-accent-teal/10 px-1 rounded">mini</span>
      </div>
    </div>
  )
}
