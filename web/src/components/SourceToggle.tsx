import type { SourceKey } from '../types'
import { SOURCE_LABELS, SOURCES } from '../types'

interface Props {
  value: SourceKey
  onChange: (s: SourceKey) => void
}

export function SourceToggle({ value, onChange }: Props) {
  return (
    <div className="source-toggle" role="group" aria-label="Odds source">
      {SOURCES.map((s) => (
        <button
          key={s}
          type="button"
          className={s === value ? 'active' : ''}
          onClick={() => onChange(s)}
        >
          {SOURCE_LABELS[s]}
        </button>
      ))}
    </div>
  )
}
