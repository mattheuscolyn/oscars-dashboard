interface Props {
  url?: string
  alt: string
  size?: 'sm' | 'md'
}

export function PosterThumb({ url, alt, size = 'sm' }: Props) {
  if (!url) {
    return (
      <span
        className={`poster-thumb placeholder ${size}`}
        aria-hidden
        title={alt}
      />
    )
  }
  return (
    <img
      className={`poster-thumb ${size}`}
      src={url}
      alt=""
      loading="lazy"
      decoding="async"
      width={size === 'md' ? 40 : 28}
      height={size === 'md' ? 60 : 42}
      title={alt}
    />
  )
}
